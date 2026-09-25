#!/usr/bin/env python3
"""Run only checks explicitly listed in verification.json; optional report output is explicit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


WORK_ID = re.compile(r"^W-\d{3,}$")


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def input_fingerprint(root: Path, patterns: list[str]) -> str:
    import fnmatch

    tracked = git(root, "ls-files", "-co", "--exclude-standard").splitlines()
    selected = sorted(p.replace("\\", "/") for p in tracked if any(fnmatch.fnmatch(p.replace("\\", "/"), pat) for pat in patterns))
    digest = hashlib.sha256()
    for name in selected:
        path = root / name
        if not path.is_file():
            continue
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run(root: Path, selected: list[str], milestone: str | None) -> tuple[dict[str, Any], int]:
    config_path = root / "verification.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read verification.json: {exc}") from exc
    if not isinstance(config, dict) or set(config) != {"schema_version", "checks", "review_methods"} or type(config.get("schema_version")) is not int or config.get("schema_version") != 1 or not isinstance(config.get("checks"), list) or not isinstance(config.get("review_methods"), list):
        raise RuntimeError("verification.json must use the exact version-1 schema with checks and review_methods arrays")
    all_checks = {c.get("id"): c for c in config["checks"] if isinstance(c, dict) and isinstance(c.get("id"), str)}
    if len(all_checks) != len(config["checks"]):
        raise RuntimeError("verification check IDs must be unique")
    requested = selected or list(all_checks)
    unknown = [check_id for check_id in requested if check_id not in all_checks]
    if unknown:
        raise RuntimeError(f"unknown configured check ID(s): {', '.join(unknown)}")
    if milestone and not WORK_ID.fullmatch(milestone):
        raise RuntimeError("milestone must be a work ID such as W-001")

    source_commit = git(root, "rev-parse", "HEAD")
    dirty = bool(git(root, "status", "--porcelain", "--untracked-files=all"))
    results: list[dict[str, Any]] = []
    overall = 0
    for check_id in requested:
        check = all_checks[check_id]
        argv = check.get("argv")
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            raise RuntimeError(f"configured check {check_id} needs argv as an array of strings")
        if check.get("kind", "command") != "command":
            raise RuntimeError(f"configured check {check_id} is not an executable command")
        command = list(argv)
        if milestone and check_id == "record-integrity":
            command.extend(["--work-id", milestone])
        env = os.environ.copy()
        # Candidate checks run without ambient GitHub credentials.
        env.pop("GITHUB_TOKEN", None)
        env.pop("GH_TOKEN", None)
        started = time.time()
        try:
            proc = subprocess.run(
                command, cwd=root, env=env, text=True, encoding="utf-8", errors="replace",
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
                timeout=int(check.get("timeout_seconds", 1800)), shell=False,
            )
            exit_status = proc.returncode
            output = proc.stdout
            if exit_status == 0:
                result = "pass"
            elif exit_status == 2:
                result = "not_discovered" if check.get("test_expectation") else "missing_evidence"
            elif exit_status == 3:
                result = "unable_to_verify"
            else:
                result = "fail"
            discovered = selected_count = skipped = None
            if check.get("test_expectation"):
                marker = None
                for line in output.splitlines():
                    if line.startswith("FIXTURE_SUMMARY "):
                        try:
                            marker = json.loads(line[len("FIXTURE_SUMMARY "):])
                        except json.JSONDecodeError:
                            marker = None
                if marker is None:
                    result = "not_discovered"
                    exit_status = 2 if exit_status == 0 else exit_status
                    discovered = selected_count = 0
                    skipped = 0
                    output += "\nRequired fixture summary missing."
                else:
                    raw_counts = (marker.get("discovered"), marker.get("selected"), marker.get("skipped"), marker.get("failures", 0))
                    if not isinstance(marker, dict) or not all(type(value) is int and value >= 0 for value in raw_counts):
                        discovered = selected_count = skipped = 0
                        result = "not_discovered"
                        exit_status = 2 if exit_status == 0 else exit_status
                        output += "\nRequired fixture summary has invalid counters."
                        raw_counts = None
                    if raw_counts is None:
                        pass
                    else:
                        discovered, selected_count, skipped, failures = raw_counts
                        if failures:
                            result = "fail"
                            if exit_status == 0:
                                exit_status = 1
                    minimum = int(check.get("minimum_discovered", 1))
                    if result != "fail" and (discovered < minimum or selected_count < minimum or selected_count > discovered or skipped):
                        result = "skipped" if skipped else "not_discovered"
                        exit_status = 2 if exit_status == 0 else exit_status
            elapsed = round(time.time() - started, 3)
        except subprocess.TimeoutExpired as exc:
            result, exit_status, output, elapsed = "unable_to_verify", None, str(exc), int(check.get("timeout_seconds", 1800))
            discovered = selected_count = skipped = None
        except OSError as exc:
            result, exit_status, output, elapsed = "unable_to_verify", None, str(exc), 0
            discovered = selected_count = skipped = None
        if result != "pass":
            overall = max(overall, 3 if result == "unable_to_verify" else 2 if result in {"missing_evidence", "not_discovered", "skipped"} else 1)
        results.append({
            "check_id": check_id,
            "command": command,
            "exit_status": exit_status,
            "result": result,
            "elapsed_seconds": elapsed,
            "discovered_tests": discovered,
            "selected_tests": selected_count,
            "skipped_tests": skipped,
            "watched_paths": check.get("watched_paths", []),
            "source_fingerprint": input_fingerprint(root, check.get("watched_paths", [])) if dirty else None,
            "output": output[-12000:],
        })

    report = {
        "schema_version": 1,
        "source_commit": source_commit,
        "working_tree_dirty": dirty,
        "runner": "scripts/run_verification.py",
        "python": sys.version.split()[0],
        "uv": subprocess.run(["uv", "--version"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout.strip(),
        "environment": os.environ.get("RUNNER_OS", os.name),
        "milestone": milestone,
        "outcome": "passed" if overall == 0 else "failure" if overall == 1 else "missing_evidence_or_test_discovery" if overall == 2 else "unable_to_verify",
        "checks": results,
    }
    return report, overall


def main() -> int:
    parser = argparse.ArgumentParser(description="Run configured project checks without reading commands from work records")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="append", default=[], help="configured check ID; repeat to select several")
    parser.add_argument("--milestone", help="focus the record-integrity check on this work ID")
    parser.add_argument("--report", type=Path, help="explicitly write the machine-readable run report to this path")
    args = parser.parse_args()
    try:
        report, code = run(args.root.resolve(), args.check, args.milestone)
    except Exception as exc:
        report, code = {"schema_version": 1, "outcome": "unable_to_verify", "error": str(exc), "checks": []}, 3
    for check in report.get("checks", []):
        print(f"{check['check_id']}: {check['result']} (exit={check['exit_status']})")
        if check.get("discovered_tests") is not None:
            print(f"  fixtures: discovered={check['discovered_tests']} selected={check['selected_tests']} skipped={check['skipped_tests']}")
    if report.get("error"):
        print(f"verification unable to run: {report['error']}", file=sys.stderr)
    if args.report:
        target = args.report if args.report.is_absolute() else args.root.resolve() / args.report
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"report: {target}")
    print(f"verification: {report['outcome']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
