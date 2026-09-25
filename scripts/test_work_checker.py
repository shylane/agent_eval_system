#!/usr/bin/env python3
"""Synthetic-only integration fixtures for scripts/check_work.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from check_work import parse_frontmatter, validate


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "work_records" / "valid_completion"


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def read_record(root: Path, item_id: str = "W-900") -> tuple[dict[str, Any], str]:
    path = root / "work" / f"{item_id}.md"
    text = path.read_text(encoding="utf-8")
    data, _, error = parse_frontmatter(text)
    if error or data is None:
        raise AssertionError(error)
    return data, text


def write_record(root: Path, data: dict[str, Any], body: str, item_id: str = "W-900") -> None:
    text = "---\n" + json.dumps(data, indent=2) + "\n---\n" + body
    (root / "work" / f"{item_id}.md").write_text(text, encoding="utf-8")


class FixtureRepo:
    """Construct an isolated synthetic history with a proposed item and a valid completion."""

    def __init__(self, final_status: str = "done"):
        self.temp = tempfile.TemporaryDirectory(prefix="work-record-fixture-")
        self.root = Path(self.temp.name)
        shutil.copytree(FIXTURE, self.root, dirs_exist_ok=True)
        git(self.root, "init", "--initial-branch=main")
        git(self.root, "config", "user.name", "Fixture Runner")
        git(self.root, "config", "user.email", "fixture@example.invalid")
        git(self.root, "add", "--all")
        git(self.root, "commit", "-m", "synthetic proposed item")
        self.criteria_baseline = git(self.root, "rev-parse", "HEAD")
        git(self.root, "switch", "-c", "fixture-work")

        data, body = read_record(self.root)
        data["authorization_ref"] = "fixture:explicit synthetic test scope"
        data["accepted_criteria_commit"] = self.criteria_baseline
        data["implementation_base_commit"] = self.criteria_baseline
        write_record(self.root, data, body)
        self.set_status("ready", "unassigned", "Begin synthetic work")
        self.commit("synthetic ready")
        self.set_status("in_progress", "fixture-agent", "Run the configured fixture check")
        self.commit("synthetic work started")

        (self.root / "src" / "behavior.txt").write_text("synthetic implementation\n", encoding="utf-8")
        self.commit("synthetic implementation checkpoint")
        self.source_commit = git(self.root, "rev-parse", "HEAD")
        self.evidence = {
            "criterion_id": "W-900-AC1",
            "source_commit": self.source_commit,
            "source_fingerprint": None,
            "criteria_baseline_commit": self.criteria_baseline,
            "check_id": "checker-fixtures",
            "command": ["python", "scripts/test_work_checker.py"],
            "exit_status": 0,
            "result": "pass",
            "applicable": True,
            "summary": "Ten required synthetic fixture tests were discovered, selected, and passed.",
            "location": "case.json",
            "provenance": "runner_observed",
            "environment": "isolated temporary Git repository; Python stdlib",
            "discovered_tests": 10,
            "selected_tests": 10,
            "skipped_tests": 0,
        }
        data, body = read_record(self.root)
        data["evidence"] = [self.evidence.copy()]
        write_record(self.root, data, body)
        if final_status in {"in_review", "done"}:
            self.set_status("in_review", "fixture-agent", "Request synthetic independent review")
            self.commit("synthetic in review")
            self.review_revision = git(self.root, "rev-parse", "HEAD")
        if final_status == "done":
            self.finish_review()
        self.final_status = final_status

    def set_status(self, status: str, owner: str, action: str) -> None:
        roadmap = self.root / "roadmap.md"
        text = roadmap.read_text(encoding="utf-8")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("| W-900 | "):
                lines[index] = f"| W-900 | [Synthetic negative experiment](work/W-900.md) | P1 | {status} | — | — | {owner} | {action} |"
                break
        roadmap.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def commit(self, message: str) -> None:
        git(self.root, "add", "--all")
        git(self.root, "commit", "-m", message)

    def finish_review(self) -> None:
        report = self.root / "work" / "reviews" / "W-900-review.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            f"# Synthetic review\n\nVerdict: ready\nRevision: `{self.review_revision}`\n"
            f"Accepted criteria: `{self.criteria_baseline}`\n\nNo findings. Synthetic fixture only.\n",
            encoding="utf-8",
        )
        data, body = read_record(self.root)
        data["reviews"] = [{
            "role": "independent",
            "assessed_source_commit": self.review_revision,
            "criteria_baseline_commit": self.criteria_baseline,
            "rubric_version": "review-rubric-v1",
            "verdict": "ready",
            "report": "work/reviews/W-900-review.md",
            "model": None,
            "reasoning_effort": None,
            "findings": [],
        }]
        write_record(self.root, data, body)
        self.set_status("done", "fixture-agent", "Preserve the historical result")
        self.commit("synthetic done")

    def close(self) -> None:
        self.temp.cleanup()


def findings(result: dict[str, Any], rule_id: str) -> list[dict[str, Any]]:
    return [finding for finding in result["findings"] if finding["rule_id"] == rule_id]


class WorkCheckerFixtures(unittest.TestCase):
    def test_valid_completion(self) -> None:
        repo = FixtureRepo()
        try:
            result = validate(repo.root, "main")
            self.assertEqual(result["exit_code"], 0, result)
            self.assertNotIn("failure", result["outcome"])
            self.assertFalse([f for f in result["findings"] if f["severity"] in {"blocking", "missing", "unable"}], result)
        finally:
            repo.close()

    def test_missing_and_stale_evidence(self) -> None:
        missing = FixtureRepo("in_review")
        try:
            data, body = read_record(missing.root)
            data["evidence"] = []
            write_record(missing.root, data, body)
            result = validate(missing.root, "main")
            self.assertEqual(result["exit_code"], 2, result)
            self.assertTrue(findings(result, "WRK007"), result)
        finally:
            missing.close()

        stale = FixtureRepo("in_review")
        try:
            with (stale.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# changed after evidence\n")
            result = validate(stale.root, "main")
            self.assertEqual(result["exit_code"], 2, result)
            self.assertTrue(findings(result, "WRK008"), result)
        finally:
            stale.close()

    def test_incomplete_required_dependency(self) -> None:
        repo = FixtureRepo()
        try:
            child = {
                "schema_version": 1, "id": "W-901", "kind": "task", "authorization_ref": None,
                "accepted_criteria_commit": None, "implementation_base_commit": None,
                "completion_disposition": "required", "ledger_refs": [],
                "criteria": [{"id": "W-901-AC1", "required": True, "behavior": "A child result", "verification_method": "Review the fixture"}],
                "evidence": [], "decisions": [], "resolutions": [], "reviews": [], "blocker": None, "disposition": None,
            }
            body = "\n# Child\n\n## Outcome\nA child.\n\n## Scope\nIncluded: fixture.\n\nExcluded: product.\n\n## Acceptance criteria\nStructured metadata.\n\n## Execution checkpoint\nNot started.\n\n## Decisions and changes\nNone.\n\n## Evidence\nNone.\n\n## Review\nNone.\n"
            (repo.root / "work" / "W-901.md").write_text("---\n" + json.dumps(child, indent=2) + "\n---\n" + body, encoding="utf-8")
            roadmap = repo.root / "roadmap.md"
            text = roadmap.read_text(encoding="utf-8") + "| W-901 | [Child](work/W-901.md) | P2 | proposed | W-900 | — | unassigned | Define fixture work |\n"
            roadmap.write_text(text, encoding="utf-8")
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK006"), result)
        finally:
            repo.close()

    def test_unapproved_accepted_criteria_change(self) -> None:
        repo = FixtureRepo()
        try:
            data, body = read_record(repo.root)
            data["criteria"][0]["behavior"] = "Skip the comparison and claim success."
            write_record(repo.root, data, body)
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK010"), result)
        finally:
            repo.close()

    def test_skipped_or_undiscovered_tests(self) -> None:
        for discovered, selected, skipped in ((9, 9, 1), (0, 0, 0)):
            repo = FixtureRepo("in_review")
            try:
                data, body = read_record(repo.root)
                data["evidence"][0]["discovered_tests"] = discovered
                data["evidence"][0]["selected_tests"] = selected
                data["evidence"][0]["skipped_tests"] = skipped
                write_record(repo.root, data, body)
                result = validate(repo.root, "main")
                self.assertTrue(findings(result, "WRK011"), result)
            finally:
                repo.close()

    def test_uncorroborated_approval(self) -> None:
        repo = FixtureRepo()
        try:
            data, body = read_record(repo.root)
            previous = data["criteria"][0]["behavior"]
            proposed = "Skip the comparison and claim success."
            data["criteria"][0]["behavior"] = proposed
            data["decisions"] = [{
                "affected_criteria": ["W-900-AC1"], "previous_wording": previous,
                "proposed_wording": proposed, "change_type": "relax", "reason": "fixture reason",
                "supporting_evidence": "fixture evidence", "user_impact": "fixture impact",
                "verification_impact": "fixture impact", "approval_source": "user",
                "approval_ref": "user said approved",
            }]
            write_record(repo.root, data, body)
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK015"), result)
        finally:
            repo.close()

    def test_verification_rule_change_requires_inspection(self) -> None:
        repo = FixtureRepo("in_review")
        try:
            config_path = repo.root / "verification.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["checks"][1]["minimum_discovered"] = 10
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK012"), result)
            self.assertTrue(findings(result, "WRK008") or findings(result, "WRK011"), result)
        finally:
            repo.close()

    def test_negative_experiment_result_can_satisfy_contract(self) -> None:
        repo = FixtureRepo()
        try:
            data, body = read_record(repo.root)
            data["evidence"][0]["summary"] = "The hypothesis was rejected; the agreed comparison and reporting method completed successfully."
            write_record(repo.root, data, body)
            result = validate(repo.root, "main")
            self.assertEqual(data["evidence"][0]["result"], "pass")
            self.assertEqual(result["exit_code"], 0, result)
            self.assertFalse([f for f in result["findings"] if f["severity"] in {"blocking", "missing", "unable"}], result)
        finally:
            repo.close()

    def test_historical_completion_is_preserved(self) -> None:
        repo = FixtureRepo()
        try:
            data_before, _ = read_record(repo.root)
            recorded = data_before["evidence"][0].copy()
            with (repo.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# later revision; history is not erased\n")
            result = validate(repo.root, "main")
            data_after, _ = read_record(repo.root)
            self.assertEqual(data_after["evidence"][0], recorded)
            self.assertTrue(any(f["severity"] == "warning" and f["rule_id"] in {"WRK008", "WRK009"} for f in result["findings"]), result)
            self.assertFalse([f for f in result["findings"] if f["severity"] in {"blocking", "missing", "unable"}], result)
        finally:
            repo.close()

    def test_nested_schema_and_removed_scope_are_blocked(self) -> None:
        repo = FixtureRepo()
        try:
            data, body = read_record(repo.root)
            data["criteria"][0]["extra"] = "unknown fields cannot be ignored"
            write_record(repo.root, data, body)
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK001"), result)

            data["criteria"][0].pop("extra")
            write_record(repo.root, data, body)
            roadmap = repo.root / "roadmap.md"
            text = "\n".join(line for line in roadmap.read_text(encoding="utf-8").splitlines() if not line.startswith("| W-900 |")) + "\n"
            roadmap.write_text(text, encoding="utf-8")
            (repo.root / "work" / "W-900.md").unlink()
            repo.commit("synthetic removal of required scope")
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK006"), result)
        finally:
            repo.close()


def main() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkCheckerFixtures)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    discovered = suite.countTestCases()
    selected = result.testsRun
    skipped = len(result.skipped)
    print("FIXTURE_SUMMARY " + json.dumps({"discovered": discovered, "selected": selected, "skipped": skipped, "failures": len(result.failures) + len(result.errors)}))
    return 0 if result.wasSuccessful() and skipped == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
