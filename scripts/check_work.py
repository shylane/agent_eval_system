#!/usr/bin/env python3
"""Read-only integrity and completion checker for roadmap-linked work records."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


SCHEMA_VERSION = 1
WORK_ID = re.compile(r"^W-\d{3,}$")
CRITERION_ID = re.compile(r"^(W-\d{3,})-AC\d+$")
SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.I)
PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|placeholder|fill this)\b", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|fixtures?|goldens?|expected)(/|$)|(^|/)test_[^/]+\.py$|_test\.py$", re.I)
ENFORCEMENT_PATHS = {
    "verification.json",
    "work/policy.md",
    "work/review-procedure.md",
    "work/REVIEW_REPORT_TEMPLATE.md",
    "work/reviewer-config.json",
    "scripts/check_work.py",
    "scripts/run_verification.py",
}
TOP_FIELDS = {
    "schema_version", "id", "kind", "authorization_ref", "accepted_criteria_commit",
    "implementation_base_commit", "completion_disposition", "ledger_refs", "criteria",
    "evidence", "decisions", "resolutions", "reviews", "blocker", "disposition",
}
STATUSES = {"proposed", "ready", "in_progress", "in_review", "done", "blocked", "deferred", "cancelled"}
KINDS = {"milestone", "feature", "task", "experiment"}
PROVENANCE = {"agent_reported", "runner_observed", "trusted_ci"}
RESULTS = {"pass", "fail", "skipped", "not_discovered", "unable_to_verify"}
APPROVAL_SOURCES = {"user", "delegated_policy", "not_required", "unverified"}
REVIEW_ROLES = {"independent", "domain_owner", "author", "self"}
REVIEW_VERDICTS = {"ready", "changes_required", "unable_to_verify"}
CRITERION_FIELDS = {"id", "required", "behavior", "verification_method"}
EVIDENCE_FIELDS = {
    "criterion_id", "source_commit", "source_fingerprint", "criteria_baseline_commit", "check_id", "command",
    "exit_status", "result", "applicable", "summary", "location", "provenance", "environment",
    "discovered_tests", "selected_tests", "skipped_tests",
}
DECISION_FIELDS = {
    "affected_criteria", "previous_wording", "proposed_wording", "change_type", "reason", "supporting_evidence",
    "user_impact", "verification_impact", "approval_source", "approval_ref",
}
RESOLUTION_FIELDS = {"finding_id", "disposition", "evidence", "approval_ref"}
REVIEW_FIELDS = {
    "role", "assessed_source_commit", "criteria_baseline_commit", "rubric_version", "verdict", "report",
    "model", "reasoning_effort", "findings",
}


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str | None, str]:
    if not text.startswith("---\n"):
        return None, None, "missing opening frontmatter delimiter"
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, None, "missing closing frontmatter delimiter"
    raw = text[4:end]
    try:
        data = json.loads(raw, object_pairs_hook=_pairs_no_duplicates)
    except (json.JSONDecodeError, ValueError) as exc:
        return None, raw, f"invalid JSON frontmatter: {exc}"
    if not isinstance(data, dict):
        return None, raw, "frontmatter must be a JSON object"
    return data, raw, ""


def git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=root, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed ({proc.returncode})")
    return proc.stdout.strip()


def valid_commit(root: Path, value: Any) -> bool:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        return False
    return subprocess.run(
        ["git", "cat-file", "-e", f"{value}^{{commit}}"], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode == 0


def parse_roadmap(text: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    rows: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    header: list[str] | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if header is None and cells and cells[0] == "ID":
            header = cells
            expected = ["ID", "Work item", "Priority", "Status", "Parent", "Depends on", "Owner", "Next action"]
            if header != expected:
                errors.append(f"line {line_no}: roadmap columns must be {expected}")
            continue
        if header is None or not cells or not cells[0].startswith("W-"):
            continue
        if len(cells) != 8:
            errors.append(f"line {line_no}: roadmap work row must contain exactly 8 cells")
            continue
        item_id = cells[0]
        if item_id in rows:
            errors.append(f"line {line_no}: duplicate roadmap ID {item_id}")
        link = re.search(r"\[[^\]]+\]\(([^)]+)\)", cells[1])
        rows[item_id] = {
            "id": item_id, "link": link.group(1) if link else "", "priority": cells[2],
            "status": cells[3], "parent": cells[4], "depends_on": cells[5],
            "owner": cells[6], "next_action": cells[7], "line": str(line_no),
        }
    if header is None:
        errors.append("roadmap table with required columns not found")
    return rows, errors


def markdown_links(text: str) -> list[str]:
    # Exclude fenced code so examples do not become repository dependencies.
    cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", cleaned)


def is_placeholder(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip() or bool(PLACEHOLDER.search(value))


class Checker:
    def __init__(self, root: Path, base_ref: str | None = None, focus_id: str | None = None):
        self.root = root.resolve()
        self.base_ref = base_ref
        self.focus_id = focus_id
        self.findings: list[dict[str, Any]] = []
        self.unable = False
        self.roadmap: dict[str, dict[str, str]] = {}
        self.items: dict[str, tuple[dict[str, Any], str, Path]] = {}
        self.checks: dict[str, dict[str, Any]] = {}
        self.review_methods: dict[str, dict[str, Any]] = {}
        self.base_sha = ""
        self.head_sha = ""
        self.changed_paths: set[str] = set()
        self.dirty = False
        self.done_commits: dict[str, str] = {}
        self.history_configs: dict[str, tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]] = {}

    def add(self, rule: str, severity: str, message: str, work_id: str | None = None,
            criterion_id: str | None = None, path: str | None = None) -> None:
        self.findings.append({
            "rule_id": rule, "severity": severity, "work_id": work_id,
            "criterion_id": criterion_id, "path": path, "message": message,
        })
        if severity == "unable":
            self.unable = True

    def _load_json_file(self, path: Path, name: str) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs_no_duplicates)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.add("WRK001", "unable", f"Cannot parse {name}: {exc}", path=path.relative_to(self.root).as_posix())
            return None
        if not isinstance(data, dict):
            self.add("WRK001", "unable", f"{name} must be a JSON object", path=path.relative_to(self.root).as_posix())
            return None
        return data

    def _git_setup(self) -> bool:
        try:
            if git(self.root, "rev-parse", "--is-inside-work-tree") != "true":
                raise RuntimeError("not inside a Git worktree")
            self.head_sha = git(self.root, "rev-parse", "HEAD")
            selected = self.base_ref or os.environ.get("WORK_BASE_REF") or "main"
            self.base_sha = git(self.root, "rev-parse", f"{selected}^{{commit}}")
            dirty_output = git(self.root, "status", "--porcelain", "--untracked-files=all")
            self.dirty = bool(dirty_output)
            changed = git(self.root, "diff", "--name-only", f"{self.base_sha}..HEAD", check=False)
            self.changed_paths = {p.replace("\\", "/") for p in changed.splitlines() if p}
            if self.dirty:
                dirty_paths = git(self.root, "diff", "--name-only", check=False).splitlines()
                untracked = git(self.root, "ls-files", "--others", "--exclude-standard", check=False).splitlines()
                self.changed_paths.update(p.replace("\\", "/") for p in dirty_paths + untracked if p)
            return True
        except Exception as exc:  # Git context is required for immutable baselines and status history.
            self.add("WRK016", "unable", f"Git context unavailable: {exc}")
            return False

    def run(self) -> dict[str, Any]:
        if not self._git_setup():
            return self.result()
        config_path = self.root / "verification.json"
        config = self._load_json_file(config_path, "verification.json")
        if config is None:
            return self.result()
        if set(config) != {"schema_version", "checks", "review_methods"}:
            self.add("WRK001", "blocking", "verification.json needs exactly schema_version, checks, and review_methods", path="verification.json")
        if type(config.get("schema_version")) is not int or config.get("schema_version") != 1 or not isinstance(config.get("checks"), list):
            self.add("WRK001", "unable", "verification.json schema_version must be 1 with a checks array", path="verification.json")
            return self.result()
        for check in config["checks"]:
            if not isinstance(check, dict) or not isinstance(check.get("id"), str) or check["id"] in self.checks:
                self.add("WRK001", "blocking", "verification check IDs must be unique objects", path="verification.json")
                continue
            required = {"id", "argv", "test_expectation", "minimum_discovered", "watched_paths"}
            allowed = required | {"timeout_seconds", "kind"}
            if not required <= set(check) or set(check) - allowed:
                self.add("WRK001", "blocking", f"check {check['id']} fields differ from schema", path="verification.json")
            self.checks[check["id"]] = check
            if not re.fullmatch(r"[a-z][a-z0-9-]*", check["id"]):
                self.add("WRK001", "blocking", f"invalid check ID {check['id']}", path="verification.json")
            if not isinstance(check.get("argv"), list) or not check["argv"] or not all(isinstance(x, str) and x for x in check["argv"]):
                self.add("WRK001", "blocking", f"check {check['id']} argv must be a nonempty array of strings", path="verification.json")
            if type(check.get("test_expectation")) is not bool or type(check.get("minimum_discovered")) is not int or check.get("minimum_discovered", -1) < 0:
                self.add("WRK001", "blocking", f"check {check['id']} has invalid test expectation/count", path="verification.json")
            if check.get("kind", "command") != "command":
                self.add("WRK001", "blocking", f"check {check['id']} kind must be command", path="verification.json")
            if check.get("timeout_seconds") is not None and (type(check["timeout_seconds"]) is not int or check["timeout_seconds"] < 1):
                self.add("WRK001", "blocking", f"check {check['id']} timeout_seconds must be a positive integer", path="verification.json")
            if not isinstance(check.get("watched_paths"), list) or not all(isinstance(p, str) and p and not p.startswith(("/", "\\")) and ".." not in PurePosixPath(p).parts for p in check.get("watched_paths", [])):
                self.add("WRK001", "blocking", f"check {check['id']} watched_paths must be repository-relative patterns", path="verification.json")
        review_methods = config.get("review_methods")
        if not isinstance(review_methods, list):
            self.add("WRK001", "blocking", "verification.json review_methods must be an array", path="verification.json")
        else:
            for method in review_methods:
                required = {"id", "procedure", "report_template", "required_reviewer_role"}
                if not isinstance(method, dict) or set(method) != required or not isinstance(method.get("id"), str) or method["id"] in self.review_methods:
                    self.add("WRK001", "blocking", "review methods need unique IDs and the exact declared fields", path="verification.json")
                    continue
                self.review_methods[method["id"]] = method
                if not re.fullmatch(r"[a-z][a-z0-9-]*", method["id"]) or method.get("required_reviewer_role") not in {"independent", "domain_owner"}:
                    self.add("WRK001", "blocking", f"review method {method['id']} has invalid ID or reviewer role", path="verification.json")
                for field in ("procedure", "report_template"):
                    ref = method.get(field)
                    target = (self.root / ref).resolve() if isinstance(ref, str) else self.root.parent
                    if not isinstance(ref, str) or self.root not in target.parents or not target.is_file():
                        self.add("WRK001", "blocking", f"review method {method['id']} {field} must resolve inside the repository", path="verification.json")
                if method["id"] in self.checks:
                    self.add("WRK001", "blocking", f"review method ID also names an executable check: {method['id']}", path="verification.json")

        reviewer_config = self._load_json_file(self.root / "work" / "reviewer-config.json", "work/reviewer-config.json")
        if reviewer_config is not None:
            expected = {"schema_version", "preferred_model", "reasoning_effort", "required_reviewer_role", "fallback"}
            if set(reviewer_config) != expected or type(reviewer_config.get("schema_version")) is not int or reviewer_config.get("schema_version") != 1:
                self.add("WRK001", "blocking", "reviewer-config.json fields or version do not match schema v1", path="work/reviewer-config.json")
            if reviewer_config.get("preferred_model") is not None and not isinstance(reviewer_config.get("preferred_model"), str):
                self.add("WRK001", "blocking", "preferred_model must be a model name or null", path="work/reviewer-config.json")
            if reviewer_config.get("reasoning_effort") is not None and not isinstance(reviewer_config.get("reasoning_effort"), str):
                self.add("WRK001", "blocking", "reasoning_effort must be an effort name or null", path="work/reviewer-config.json")
            if reviewer_config.get("required_reviewer_role") not in {"independent", "domain_owner"} or is_placeholder(reviewer_config.get("fallback")):
                self.add("WRK001", "blocking", "reviewer role and unavailable-reviewer rule must be explicit", path="work/reviewer-config.json")

        roadmap_path = self.root / "roadmap.md"
        try:
            roadmap_text = roadmap_path.read_text(encoding="utf-8")
        except OSError as exc:
            self.add("WRK001", "unable", f"Cannot read roadmap.md: {exc}", path="roadmap.md")
            return self.result()
        self.roadmap, road_errors = parse_roadmap(roadmap_text)
        for error in road_errors:
            self.add("WRK001", "blocking", error, path="roadmap.md")
        self._load_records()
        self._check_roadmap()
        self._check_graphs()
        self._check_history()
        self._check_items()
        self._check_parent_completion()
        self._check_changed_paths()
        return self.result()

    def result(self) -> dict[str, Any]:
        if self.unable:
            outcome, code = "unable_to_check", 3
        elif any(f["severity"] == "blocking" for f in self.findings):
            outcome, code = "failure", 1
        elif any(f["severity"] == "missing" for f in self.findings):
            outcome, code = "missing_evidence", 2
        else:
            outcome, code = "passed", 0
        order = {"blocking": 0, "missing": 1, "unable": 2, "review": 3, "warning": 4, "info": 5}
        findings = sorted(self.findings, key=lambda f: (order.get(f["severity"], 9), f["rule_id"], f["work_id"] or "", f["path"] or ""))
        return {"outcome": outcome, "exit_code": code, "focused_work_id": self.focus_id, "findings": findings}

    def _load_records(self) -> None:
        for item_id, row in self.roadmap.items():
            path_text = row["link"].split("#", 1)[0]
            if not path_text:
                self.add("WRK002", "blocking", "roadmap row must link to one detailed work item", item_id, path="roadmap.md")
                continue
            candidate = (self.root / unquote(path_text)).resolve()
            if self.root not in candidate.parents or not candidate.is_file():
                self.add("WRK002", "blocking", f"work item link does not resolve: {path_text}", item_id, path="roadmap.md")
                continue
            if candidate.name != f"{item_id}.md" or candidate.parent != (self.root / "work").resolve():
                self.add("WRK002", "blocking", f"ID must map to work/{item_id}.md", item_id, path=path_text)
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except OSError as exc:
                self.add("WRK001", "unable", f"cannot read work item: {exc}", item_id, path=path_text)
                continue
            data, _, error = parse_frontmatter(text)
            if error:
                self.add("WRK001", "blocking", error, item_id, path=path_text)
                continue
            assert data is not None
            if item_id in self.items:
                self.add("WRK002", "blocking", "duplicate work item ID", item_id, path=path_text)
                continue
            self.items[item_id] = (data, text, candidate)
        for candidate in (self.root / "work").glob("W-*.md"):
            if candidate.stem not in self.roadmap:
                self.add("WRK002", "blocking", "orphan work item file has no roadmap row", candidate.stem, path=candidate.relative_to(self.root).as_posix())

    def _check_roadmap(self) -> None:
        if self.focus_id and self.focus_id not in self.roadmap:
            self.add("WRK004", "blocking", f"focused work ID does not exist: {self.focus_id}", self.focus_id, path="roadmap.md")
        for item_id, row in self.roadmap.items():
            if not WORK_ID.fullmatch(item_id):
                self.add("WRK002", "blocking", "invalid stable work ID", item_id, path="roadmap.md")
            if row["priority"] not in {"P0", "P1", "P2", "P3"}:
                self.add("WRK001", "blocking", f"invalid priority {row['priority']}", item_id, path="roadmap.md")
            if row["status"] not in STATUSES:
                self.add("WRK003", "blocking", f"invalid status {row['status']}", item_id, path="roadmap.md")
            if is_placeholder(row["owner"]) or is_placeholder(row["next_action"]):
                self.add("WRK014", "blocking", "roadmap owner and next action must be explicit", item_id, path="roadmap.md")
            for cell_name in ("parent", "depends_on"):
                cell = row[cell_name]
                ids = [] if cell == "—" else [part.strip() for part in cell.split(",") if part.strip()]
                if cell != "—" and (not ids or any(not WORK_ID.fullmatch(ref) for ref in ids)):
                    self.add("WRK004", "blocking", f"invalid {cell_name} syntax: {cell}", item_id, path="roadmap.md")
                if cell_name == "parent" and len(ids) > 1:
                    self.add("WRK004", "blocking", "parent must contain one ID or —", item_id, path="roadmap.md")
                if len(ids) != len(set(ids)):
                    self.add("WRK004", "blocking", f"duplicate ID in {cell_name}", item_id, path="roadmap.md")
                row[cell_name + "_ids"] = ids
            for target in [row["link"]]:
                self._check_link(target, self.root / "roadmap.md", item_id)
            if row["status"] == "blocked" and (not row["next_action"] or row["next_action"] == "—"):
                self.add("WRK003", "blocking", "blocked item needs a concrete next action", item_id, path="roadmap.md")

    def _check_link(self, target: str, source: Path, item_id: str | None = None) -> None:
        parsed = urlsplit(target)
        if parsed.scheme == "https" or target.startswith("#"):
            return
        if parsed.scheme:
            self.add("WRK002", "blocking", f"external links must use HTTPS: {target}", item_id, path=source.relative_to(self.root).as_posix())
            return
        path_part = unquote(parsed.path)
        if not path_part:
            return
        resolved = (source.parent / path_part).resolve()
        if self.root not in resolved.parents and resolved != self.root:
            self.add("WRK002", "blocking", f"link escapes the repository: {target}", item_id, path=source.relative_to(self.root).as_posix())
        elif not resolved.exists():
            self.add("WRK002", "blocking", f"local link does not resolve: {target}", item_id, path=source.relative_to(self.root).as_posix())

    def _check_graphs(self) -> None:
        for item_id, row in self.roadmap.items():
            if item_id not in self.items:
                continue
            for target in row["parent_ids"] + row["depends_on_ids"]:
                if target not in self.roadmap:
                    self.add("WRK004", "blocking", f"references missing work item {target}", item_id, path="roadmap.md")
            if row["parent"] != "—" and item_id in row["parent_ids"]:
                self.add("WRK005", "blocking", "item cannot be its own parent", item_id, path="roadmap.md")
        for edge_name, field in (("parent", "parent_ids"), ("dependency", "depends_on_ids")):
            visiting: set[str] = set()
            visited: set[str] = set()

            def visit(node: str) -> None:
                if node in visiting:
                    self.add("WRK005", "blocking", f"{edge_name} cycle includes {node}", node, path="roadmap.md")
                    return
                if node in visited:
                    return
                visiting.add(node)
                row = self.roadmap.get(node, {})
                for nxt in row.get(field, []):
                    if nxt in self.roadmap:
                        visit(nxt)
                visiting.remove(node)
                visited.add(node)

            for node in self.roadmap:
                visit(node)

    @staticmethod
    def _transition_ok(old: str | None, new: str) -> bool:
        if old == new:
            return True
        allowed = {
            None: {"proposed"},
            "proposed": {"ready", "blocked", "deferred", "cancelled"},
            "ready": {"in_progress", "blocked", "deferred", "cancelled"},
            "in_progress": {"in_review", "blocked", "deferred", "cancelled"},
            "in_review": {"done", "in_progress", "blocked", "deferred", "cancelled"},
            "blocked": {"in_progress", "in_review", "deferred", "cancelled"},
            "deferred": {"proposed", "cancelled"},
            "done": set(),
            "cancelled": set(),
        }
        return new in allowed.get(old, set())

    def _check_history(self) -> None:
        try:
            base_text = git(self.root, "show", f"{self.base_sha}:roadmap.md", check=False)
            previous, _ = parse_roadmap(base_text) if base_text else ({}, [])
            commits = git(self.root, "rev-list", "--first-parent", "--reverse", f"{self.base_sha}..{self.head_sha}", check=False).splitlines()
            previous_commit = self.base_sha
            for commit in commits:
                text = git(self.root, "show", f"{commit}:roadmap.md", check=False)
                current, _ = parse_roadmap(text) if text else ({}, [])
                for removed_id in sorted(set(previous) - set(current)):
                    self.add("WRK006", "blocking", f"roadmap item {removed_id} was removed; retain it and record an explicit disposition", removed_id, path="roadmap.md")
                for item_id, row in current.items():
                    old = previous.get(item_id, {}).get("status")
                    new = row.get("status", "")
                    if not self._transition_ok(old, new):
                        self.add("WRK003", "blocking", f"invalid status transition {old or 'new'} -> {new}", item_id, path="roadmap.md")
                    if new == "done" and old != "done":
                        self.done_commits[item_id] = commit
                    if old == "deferred" and new == "proposed":
                        old_record = git(self.root, "show", f"{previous_commit}:work/{item_id}.md", check=False)
                        new_record = git(self.root, "show", f"{commit}:work/{item_id}.md", check=False)
                        old_data, _, old_error = parse_frontmatter(old_record)
                        new_data, _, new_error = parse_frontmatter(new_record)
                        old_decisions = old_data.get("decisions", []) if old_data and not old_error else []
                        new_decisions = new_data.get("decisions", []) if new_data and not new_error else []
                        if old_decisions == new_decisions:
                            self.add("WRK003", "blocking", "deferred work returned to proposed without a new decision", item_id, path="roadmap.md")
                    if new != old:
                        self._check_transition_snapshot(commit, item_id, new, row, current)
                    if new == "done":
                        self._check_parent_completion_at_commit(commit, item_id, current)
                previous = current
                previous_commit = commit
            head_text = git(self.root, "show", f"{self.head_sha}:roadmap.md", check=False)
            head_rows, _ = parse_roadmap(head_text) if head_text else ({}, [])
            for removed_id in sorted(set(head_rows) - set(self.roadmap)):
                self.add("WRK006", "blocking", f"roadmap item {removed_id} was removed from the working tree; retain it and record an explicit disposition", removed_id, path="roadmap.md")
            for item_id, row in self.roadmap.items():
                old = head_rows.get(item_id, {}).get("status")
                if old != row["status"] and not self._transition_ok(old, row["status"]):
                    self.add("WRK003", "blocking", f"invalid working-tree status transition {old or 'new'} -> {row['status']}", item_id, path="roadmap.md")
                if row["status"] == "done" and old != "done":
                    self.done_commits[item_id] = self.head_sha
        except Exception as exc:
            self.add("WRK016", "unable", f"Cannot inspect status history: {exc}", path="roadmap.md")

    def _record_at_commit(self, commit: str, item_id: str) -> tuple[dict[str, Any] | None, str]:
        record = git(self.root, "show", f"{commit}:work/{item_id}.md", check=False)
        if not record:
            return None, ""
        data, _, error = parse_frontmatter(record)
        return (data, record) if not error else (None, record)

    def _commit_artifact_exists(self, commit: str, value: Any) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        parsed = urlsplit(value)
        if parsed.scheme == "https":
            return True
        if parsed.scheme or value.startswith(("/", "\\")) or ".." in PurePosixPath(value).parts:
            return False
        return subprocess.run(
            ["git", "cat-file", "-e", f"{commit}:{unquote(value.split('#', 1)[0])}"], cwd=self.root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        ).returncode == 0

    def _verification_at_commit(self, commit: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        if commit not in self.history_configs:
            raw = git(self.root, "show", f"{commit}:verification.json", check=False)
            try:
                config = json.loads(raw, object_pairs_hook=_pairs_no_duplicates)
                checks = {entry["id"]: entry for entry in config.get("checks", []) if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
                methods = {entry["id"]: entry for entry in config.get("review_methods", []) if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
                self.history_configs[commit] = (checks, methods)
            except (json.JSONDecodeError, ValueError, AttributeError):
                self.history_configs[commit] = ({}, {})
        return self.history_configs[commit]

    def _rubric_version_at(self, commit: str) -> str | None:
        procedure = git(self.root, "show", f"{commit}:work/review-procedure.md", check=False)
        match = re.search(r"(?m)^Rubric version: `([a-z0-9-]+)`\s*$", procedure)
        return match.group(1) if match else None

    def _approval_ref_resolves_at(self, commit: str, ref: Any) -> bool:
        if not isinstance(ref, str) or not ref.strip() or PLACEHOLDER.search(ref):
            return False
        match = re.match(r"^git:([0-9a-f]{40}|[0-9a-f]{64}):(.+)$", ref, re.I)
        if match:
            return valid_commit(self.root, match.group(1)) and subprocess.run(
                ["git", "cat-file", "-e", f"{match.group(1)}:{match.group(2)}"], cwd=self.root,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            ).returncode == 0
        return self._commit_artifact_exists(commit, ref)

    def _history_evidence_complete(self, commit: str, item_id: str, data: dict[str, Any]) -> bool:
        required = {c.get("id") for c in data.get("criteria", []) if isinstance(c, dict) and c.get("required") is True}
        covered: set[str] = set()
        valid = True
        historical_checks, historical_methods = self._verification_at_commit(commit)
        entries = data.get("evidence", [])
        if not isinstance(entries, list):
            return False
        for evidence in entries:
            if not isinstance(evidence, dict) or evidence.get("criterion_id") not in required:
                valid = False
                continue
            check = historical_checks.get(evidence.get("check_id"))
            method = historical_methods.get(evidence.get("check_id"))
            if check is None and method is None:
                valid = False
                continue
            expected = check.get("argv", []) if check is not None else []
            if evidence.get("command") != expected:
                valid = False
            if evidence.get("result") != "pass" or evidence.get("applicable") is not True or evidence.get("exit_status") not in (0, None):
                valid = False
                continue
            if evidence.get("criteria_baseline_commit") != data.get("accepted_criteria_commit"):
                valid = False
            source = evidence.get("source_commit")
            fingerprint = evidence.get("source_fingerprint")
            if bool(source) == bool(fingerprint) or (source and not valid_commit(self.root, source)):
                valid = False
            if fingerprint and not re.fullmatch(r"[0-9a-f]{64}", str(fingerprint)):
                valid = False
            if not self._commit_artifact_exists(commit, evidence.get("location")):
                valid = False
            if method is not None and (evidence.get("provenance") != "agent_reported" or evidence.get("exit_status") is not None):
                valid = False
            if check is not None and check.get("test_expectation"):
                counts = (evidence.get("discovered_tests"), evidence.get("selected_tests"), evidence.get("skipped_tests"))
                minimum = check.get("minimum_discovered", 1)
                if not all(type(count) is int and count >= 0 for count in counts) or counts[0] < minimum or counts[1] < minimum or counts[1] > counts[0] or counts[2] != 0:
                    valid = False
            covered.add(evidence.get("criterion_id"))
        if required - covered:
            valid = False
        return valid

    def _check_transition_snapshot(self, commit: str, item_id: str, status: str, row: dict[str, str], roadmap: dict[str, dict[str, str]]) -> None:
        data, record_text = self._record_at_commit(commit, item_id)
        if data is None:
            self.add("WRK003", "blocking", f"{status} transition has no parseable work record at that commit", item_id, path="roadmap.md")
            return
        if status == "ready":
            if is_placeholder(data.get("authorization_ref")) or not valid_commit(self.root, data.get("accepted_criteria_commit")) or not valid_commit(self.root, data.get("implementation_base_commit")):
                self.add("WRK003", "blocking", "ready transition lacked authorization or immutable baseline references at that commit", item_id, path="roadmap.md")
            criteria = data.get("criteria")
            if not isinstance(criteria, list) or not criteria or any(
                not isinstance(c, dict) or not isinstance(c.get("required"), bool)
                or is_placeholder(c.get("id")) or is_placeholder(c.get("behavior")) or is_placeholder(c.get("verification_method"))
                for c in criteria
            ):
                self.add("WRK007", "blocking", "ready transition lacked concrete stable criteria and verification methods at that commit", item_id, path="roadmap.md")
            for heading in ("## Outcome", "## Scope", "## Execution checkpoint"):
                match = re.search(rf"{re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)", record_text, re.S)
                if is_placeholder(match.group(1).strip() if match else ""):
                    self.add("WRK014", "blocking", f"ready transition lacked concrete {heading[3:]} at that commit", item_id, path="roadmap.md")
        if status in {"in_progress", "in_review", "done"}:
            if row.get("owner") == "unassigned":
                self.add("WRK003", "blocking", f"{status} transition lacked a named owner at that commit", item_id, path="roadmap.md")
            for dependency in row.get("depends_on_ids", []):
                if roadmap.get(dependency, {}).get("status") != "done":
                    self.add("WRK004", "blocking", f"{status} transition started before dependency {dependency} was done", item_id, path="roadmap.md")
        if status == "in_review" and not self._history_evidence_complete(commit, item_id, data):
            self.add("WRK007", "blocking", "in_review transition lacked complete fresh evidence at that commit", item_id, path="roadmap.md")
        if status == "done":
            if not self._history_evidence_complete(commit, item_id, data):
                self.add("WRK007", "blocking", "done transition lacked complete applicable evidence at that commit", item_id, path="roadmap.md")
            reviews = data.get("reviews", [])
            ready_review = any(
                isinstance(review, dict)
                and review.get("role") in {"independent", "domain_owner"}
                and review.get("verdict") == "ready"
                and not review.get("findings")
                and review.get("criteria_baseline_commit") == data.get("accepted_criteria_commit")
                and review.get("rubric_version") == self._rubric_version_at(commit)
                and self._commit_artifact_exists(commit, review.get("report"))
                for review in (reviews if isinstance(reviews, list) else [])
            )
            if not ready_review:
                self.add("WRK009", "blocking", "done transition lacked an independent ready review report at that commit", item_id, path="roadmap.md")
        if status == "blocked":
            blocker = data.get("blocker")
            if not isinstance(blocker, dict) or is_placeholder(blocker.get("reason")) or is_placeholder(blocker.get("next_action")):
                self.add("WRK003", "blocking", "blocked transition lacked a reason and next action at that commit", item_id, path="roadmap.md")
        if status in {"deferred", "cancelled"}:
            disposition = data.get("disposition")
            if not isinstance(disposition, dict) or disposition.get("approval_source") not in {"user", "delegated_policy"} or not self._commit_artifact_exists(commit, disposition.get("evidence")) or not self._approval_ref_resolves_at(commit, disposition.get("approval_ref")):
                self.add("WRK015", "blocking", f"{status} transition lacked inspectable disposition evidence at that commit", item_id, path="roadmap.md")

    def _check_parent_completion_at_commit(self, commit: str, parent_id: str, roadmap: dict[str, dict[str, str]]) -> None:
        for child_id, child_row in roadmap.items():
            if parent_id not in child_row.get("parent_ids", []):
                continue
            child_data, _ = self._record_at_commit(commit, child_id)
            if child_data is None or child_data.get("completion_disposition") == "optional" or child_row.get("status") == "done":
                continue
            disposition = child_data.get("disposition")
            if child_row.get("status") not in {"deferred", "cancelled"} or not isinstance(disposition, dict) or disposition.get("approval_source") not in {"user", "delegated_policy"} or not self._commit_artifact_exists(commit, disposition.get("evidence")) or not self._approval_ref_resolves_at(commit, disposition.get("approval_ref")):
                self.add("WRK006", "blocking", f"parent was completed while required child {child_id} remained unfinished", parent_id, path="roadmap.md")

    def _check_items(self) -> None:
        for item_id, (data, text, path) in self.items.items():
            row = self.roadmap[item_id]
            rel = path.relative_to(self.root).as_posix()
            keys = set(data)
            if keys != TOP_FIELDS:
                self.add("WRK001", "blocking", f"frontmatter keys differ from schema (missing={sorted(TOP_FIELDS-keys)}, unknown={sorted(keys-TOP_FIELDS)})", item_id, path=rel)
            if type(data.get("schema_version")) is not int or data.get("schema_version") != SCHEMA_VERSION:
                self.add("WRK001", "unable", "unsupported schema_version; migrate explicitly", item_id, path=rel)
            if data.get("id") != item_id or not WORK_ID.fullmatch(str(data.get("id", ""))):
                self.add("WRK002", "blocking", "frontmatter ID must match filename and roadmap", item_id, path=rel)
            if data.get("kind") not in KINDS or data.get("completion_disposition") not in {"required", "optional"}:
                self.add("WRK001", "blocking", "invalid kind or completion_disposition", item_id, path=rel)
            arrays = ("ledger_refs", "criteria", "evidence", "decisions", "resolutions", "reviews")
            for key in arrays:
                if not isinstance(data.get(key), list):
                    self.add("WRK001", "blocking", f"{key} must be an array", item_id, path=rel)
            if not isinstance(data.get("authorization_ref"), (str, type(None))):
                self.add("WRK001", "blocking", "authorization_ref must be a string or null", item_id, path=rel)
            elif isinstance(data.get("authorization_ref"), str) and not data["authorization_ref"].strip():
                self.add("WRK001", "blocking", "unknown authorization_ref must be null, not an empty string", item_id, path=rel)
            for reference in ("accepted_criteria_commit", "implementation_base_commit"):
                value = data.get(reference)
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    self.add("WRK001", "blocking", f"{reference} must be an immutable commit string or null", item_id, path=rel)
            criteria = data.get("criteria") if isinstance(data.get("criteria"), list) else []
            seen_criteria: set[str] = set()
            for criterion in criteria:
                if not isinstance(criterion, dict):
                    self.add("WRK001", "blocking", "criterion must be an object", item_id, path=rel)
                    continue
                if set(criterion) != CRITERION_FIELDS:
                    self.add("WRK001", "blocking", f"criterion fields differ from schema (missing={sorted(CRITERION_FIELDS-set(criterion))}, unknown={sorted(set(criterion)-CRITERION_FIELDS)})", item_id, path=rel)
                cid = criterion.get("id")
                if not isinstance(cid, str) or not CRITERION_ID.fullmatch(cid) or not cid.startswith(item_id + "-") or cid in seen_criteria:
                    self.add("WRK007", "blocking", "criterion ID must be unique and stable for this work item", item_id, str(cid) if cid else None, rel)
                if cid:
                    seen_criteria.add(cid)
                if not isinstance(criterion.get("required"), bool) or is_placeholder(criterion.get("behavior")) or is_placeholder(criterion.get("verification_method")):
                    self.add("WRK007", "blocking", "criterion needs boolean required, concrete behavior, and verification_method", item_id, str(cid) if cid else None, rel)
            self._validate_nested_shapes(item_id, data, path)
            for ref in data.get("ledger_refs", []) if isinstance(data.get("ledger_refs"), list) else []:
                ledger_text = (self.root / "experiments.md").read_text(encoding="utf-8") if (self.root / "experiments.md").exists() else ""
                if not isinstance(ref, str) or not re.search(rf"^\|\s*{re.escape(ref)}\s*\|", ledger_text, re.M):
                    self.add("WRK004", "blocking", f"experiment reference does not exist: {ref}", item_id, path=rel)
            for link in markdown_links(text):
                self._check_link(link, path, item_id)
            self._check_criteria_baseline(item_id, data, path)
            self._check_decisions(item_id, data, path)
            self._check_lifecycle(item_id, data, row, text, path)
            if row["status"] in {"in_review", "done"}:
                self._check_evidence(item_id, data, path)
            if row["status"] == "done":
                self._check_reviews(item_id, data, path)

    def _validate_nested_shapes(self, item_id: str, data: dict[str, Any], path: Path) -> None:
        rel = path.relative_to(self.root).as_posix()

        def shape(value: Any, fields: set[str], label: str) -> bool:
            if not isinstance(value, dict):
                self.add("WRK001", "blocking", f"{label} must be an object", item_id, path=rel)
                return False
            if set(value) != fields:
                self.add("WRK001", "blocking", f"{label} fields differ from schema (missing={sorted(fields-set(value))}, unknown={sorted(set(value)-fields)})", item_id, path=rel)
                return False
            return True

        def required_text(value: Any, label: str) -> None:
            if is_placeholder(value):
                self.add("WRK001", "blocking", f"{label} must be concrete text", item_id, path=rel)

        for entry in data.get("evidence", []) if isinstance(data.get("evidence"), list) else []:
            if not shape(entry, EVIDENCE_FIELDS, "evidence entry"):
                continue
            for key in ("criterion_id", "check_id", "summary", "location", "provenance", "environment"):
                required_text(entry.get(key), f"evidence.{key}")
            if entry.get("source_commit") is not None and not isinstance(entry.get("source_commit"), str):
                self.add("WRK001", "blocking", "evidence.source_commit must be a string or null", item_id, path=rel)
            if entry.get("source_fingerprint") is not None and not isinstance(entry.get("source_fingerprint"), str):
                self.add("WRK001", "blocking", "evidence.source_fingerprint must be a string or null", item_id, path=rel)
            if entry.get("criteria_baseline_commit") is not None and not isinstance(entry.get("criteria_baseline_commit"), str):
                self.add("WRK001", "blocking", "evidence.criteria_baseline_commit must be a string or null", item_id, path=rel)
            if not isinstance(entry.get("command"), list) or not all(isinstance(part, str) for part in entry.get("command", [])):
                self.add("WRK001", "blocking", "evidence.command must be an argv array of strings", item_id, path=rel)
            if entry.get("exit_status") is not None and type(entry.get("exit_status")) is not int:
                self.add("WRK001", "blocking", "evidence.exit_status must be an integer or null", item_id, path=rel)
            if type(entry.get("applicable")) is not bool:
                self.add("WRK001", "blocking", "evidence.applicable must be boolean", item_id, path=rel)
            for key in ("discovered_tests", "selected_tests", "skipped_tests"):
                if entry.get(key) is not None and (type(entry.get(key)) is not int or entry.get(key) < 0):
                    self.add("WRK001", "blocking", f"evidence.{key} must be a nonnegative integer or null", item_id, path=rel)
            if entry.get("result") not in RESULTS or entry.get("provenance") not in PROVENANCE:
                self.add("WRK001", "blocking", "evidence result or provenance is outside the allowed values", item_id, path=rel)
            self._check_artifact_ref(entry.get("location"), item_id, rel, "evidence location")

        for entry in data.get("decisions", []) if isinstance(data.get("decisions"), list) else []:
            if not shape(entry, DECISION_FIELDS, "decision"):
                continue
            for key in ("reason", "supporting_evidence", "user_impact", "verification_impact"):
                required_text(entry.get(key), f"decision.{key}")
            if not isinstance(entry.get("affected_criteria"), list) or not entry.get("affected_criteria") or not all(isinstance(cid, str) and CRITERION_ID.fullmatch(cid) for cid in entry.get("affected_criteria", [])):
                self.add("WRK001", "blocking", "decision.affected_criteria must list stable criterion IDs", item_id, path=rel)
            change = entry.get("change_type")
            if change not in {"clarify", "strengthen", "relax", "remove", "add"}:
                self.add("WRK001", "blocking", "decision.change_type is outside the allowed values", item_id, path=rel)
            for key in ("previous_wording", "proposed_wording"):
                value = entry.get(key)
                if value is not None and (not isinstance(value, str) or not value.strip() or PLACEHOLDER.search(value)):
                    self.add("WRK001", "blocking", f"decision.{key} must be concrete text or null", item_id, path=rel)
                if value is None and not ((change == "add" and key == "previous_wording") or (change == "remove" and key == "proposed_wording")):
                    self.add("WRK001", "blocking", f"decision.{key} may be null only for its matching add/remove operation", item_id, path=rel)
            if entry.get("approval_source") not in APPROVAL_SOURCES:
                self.add("WRK001", "blocking", "decision.approval_source is outside the allowed values", item_id, path=rel)
            if entry.get("approval_ref") is not None and not isinstance(entry.get("approval_ref"), str):
                self.add("WRK001", "blocking", "decision.approval_ref must be a string or null", item_id, path=rel)

        for entry in data.get("resolutions", []) if isinstance(data.get("resolutions"), list) else []:
            if not shape(entry, RESOLUTION_FIELDS, "resolution"):
                continue
            for key in ("finding_id", "evidence"):
                required_text(entry.get(key), f"resolution.{key}")
            if entry.get("disposition") not in {"resolved", "open"}:
                self.add("WRK001", "blocking", "resolution.disposition is outside the allowed values", item_id, path=rel)
            if entry.get("approval_ref") is not None and not isinstance(entry.get("approval_ref"), str):
                self.add("WRK001", "blocking", "resolution.approval_ref must be a string or null", item_id, path=rel)

        for entry in data.get("reviews", []) if isinstance(data.get("reviews"), list) else []:
            if not shape(entry, REVIEW_FIELDS, "review"):
                continue
            if entry.get("role") not in REVIEW_ROLES or entry.get("verdict") not in REVIEW_VERDICTS:
                self.add("WRK001", "blocking", "review role or verdict is outside the allowed values", item_id, path=rel)
            if entry.get("model") is not None and not isinstance(entry.get("model"), str):
                self.add("WRK001", "blocking", "review.model must be a string or null", item_id, path=rel)
            if entry.get("reasoning_effort") is not None and not isinstance(entry.get("reasoning_effort"), str):
                self.add("WRK001", "blocking", "review.reasoning_effort must be a string or null", item_id, path=rel)
            if not isinstance(entry.get("findings"), list) or not all(isinstance(finding, str) and finding.strip() for finding in entry.get("findings", [])):
                self.add("WRK001", "blocking", "review.findings must be an array of finding IDs or concise references", item_id, path=rel)

        blocker = data.get("blocker")
        if blocker is not None:
            if shape(blocker, {"reason", "next_action"}, "blocker"):
                required_text(blocker.get("reason"), "blocker.reason")
                required_text(blocker.get("next_action"), "blocker.next_action")
        disposition = data.get("disposition")
        if disposition is not None:
            if shape(disposition, {"reason", "approval_source", "approval_ref", "evidence"}, "disposition"):
                required_text(disposition.get("reason"), "disposition.reason")
                required_text(disposition.get("evidence"), "disposition.evidence")
                if disposition.get("approval_source") not in {"user", "delegated_policy"}:
                    self.add("WRK001", "blocking", "disposition.approval_source must be user or delegated_policy", item_id, path=rel)
                if disposition.get("approval_ref") is not None and not isinstance(disposition.get("approval_ref"), str):
                    self.add("WRK001", "blocking", "disposition.approval_ref must be a string or null", item_id, path=rel)

    def _check_artifact_ref(self, value: Any, item_id: str, record_path: str, label: str) -> None:
        if is_placeholder(value):
            self.add("WRK007", "missing", f"{label} is missing", item_id, path=record_path)
            return
        if not isinstance(value, str):
            return
        parsed = urlsplit(value)
        if parsed.scheme == "https":
            return
        if parsed.scheme:
            self.add("WRK007", "blocking", f"{label} external links must use HTTPS", item_id, path=record_path)
            return
        target = (self.root / unquote(value.split("#", 1)[0])).resolve()
        if self.root not in target.parents or not target.is_file():
            self.add("WRK007", "blocking", f"{label} does not resolve from repository root: {value}", item_id, path=record_path)

    def _baseline_data(self, item_id: str, commit: Any, path: Path) -> dict[str, Any] | None:
        if not valid_commit(self.root, commit):
            self.add("WRK016", "unable", "accepted criteria reference is not a resolvable immutable commit", item_id, path=path.relative_to(self.root).as_posix())
            return None
        try:
            text = git(self.root, "show", f"{commit}:{path.relative_to(self.root).as_posix()}")
            data, _, error = parse_frontmatter(text)
            if error or data is None:
                self.add("WRK016", "unable", f"accepted baseline record cannot be parsed: {error}", item_id, path=path.relative_to(self.root).as_posix())
                return None
            return data
        except Exception as exc:
            self.add("WRK016", "unable", f"accepted baseline does not contain this work item: {exc}", item_id, path=path.relative_to(self.root).as_posix())
            return None

    @staticmethod
    def _criteria_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {c.get("id"): c for c in data.get("criteria", []) if isinstance(c, dict) and isinstance(c.get("id"), str)}

    def _check_criteria_baseline(self, item_id: str, data: dict[str, Any], path: Path) -> None:
        row = self.roadmap[item_id]
        status = row["status"]
        baseline = data.get("accepted_criteria_commit")
        if status in {"ready", "in_progress", "in_review", "done"}:
            if not valid_commit(self.root, baseline):
                self.add("WRK016", "unable", "accepted_criteria_commit must resolve to an immutable commit", item_id, path=path.relative_to(self.root).as_posix())
                return
            prior = self._baseline_data(item_id, baseline, path)
            if prior is None:
                return
            old, new = self._criteria_map(prior), self._criteria_map(data)
            changed = {cid for cid in set(old) | set(new) if old.get(cid) != new.get(cid)}
            if changed:
                decisions = data.get("decisions", [])
                covered = set()
                for dec in decisions if isinstance(decisions, list) else []:
                    if isinstance(dec, dict) and isinstance(dec.get("affected_criteria"), list):
                        covered.update(x for x in dec["affected_criteria"] if isinstance(x, str))
                missing = changed - covered
                if missing:
                    self.add("WRK010", "blocking", f"accepted criteria changed without decision coverage: {', '.join(sorted(missing))}", item_id, next(iter(sorted(missing))), path.relative_to(self.root).as_posix())
            base_ref = data.get("implementation_base_commit")
            if not valid_commit(self.root, base_ref):
                self.add("WRK016", "unable", "implementation_base_commit must resolve to an immutable commit", item_id, path=path.relative_to(self.root).as_posix())

    def _approval_ref_resolves(self, ref: Any) -> bool:
        if not isinstance(ref, str) or not ref.strip() or PLACEHOLDER.search(ref):
            return False
        match = re.match(r"^git:([0-9a-f]{40}|[0-9a-f]{64}):(.+)$", ref, re.I)
        if match:
            return valid_commit(self.root, match.group(1)) and subprocess.run(
                ["git", "cat-file", "-e", f"{match.group(1)}:{match.group(2)}"], cwd=self.root,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            ).returncode == 0
        parsed = urlsplit(ref)
        if parsed.scheme in {"https", "http"}:
            return False  # Online sources remain for human inspection, not mechanical corroboration.
        candidate = (self.root / unquote(ref.split("#", 1)[0])).resolve()
        return self.root in candidate.parents and candidate.is_file()

    def _check_decisions(self, item_id: str, data: dict[str, Any], path: Path) -> None:
        for decision in data.get("decisions", []) if isinstance(data.get("decisions"), list) else []:
            if not isinstance(decision, dict):
                self.add("WRK010", "blocking", "decision must be an object", item_id, path=path.relative_to(self.root).as_posix())
                continue
            required = ("affected_criteria", "previous_wording", "proposed_wording", "change_type", "reason", "supporting_evidence", "user_impact", "verification_impact", "approval_source", "approval_ref")
            if any(k not in decision for k in required) or decision.get("change_type") not in {"clarify", "strengthen", "relax", "remove", "add"} or decision.get("approval_source") not in APPROVAL_SOURCES:
                self.add("WRK010", "blocking", "decision is missing required fields or has invalid values", item_id, path=path.relative_to(self.root).as_posix())
                continue
            wording_missing = (
                (decision.get("previous_wording") is None and decision.get("change_type") != "add")
                or (decision.get("proposed_wording") is None and decision.get("change_type") != "remove")
            )
            if wording_missing or any(is_placeholder(decision.get(k)) for k in ("reason", "supporting_evidence", "user_impact", "verification_impact")):
                self.add("WRK010", "blocking", "decision wording, rationale, evidence, and impacts must be explicit", item_id, path=path.relative_to(self.root).as_posix())
            if decision.get("change_type") in {"relax", "remove"}:
                if decision.get("approval_source") not in {"user", "delegated_policy"} or not self._approval_ref_resolves(decision.get("approval_ref")):
                    self.add("WRK015", "blocking", "material reduction has no inspectable, corroborable approval source", item_id, path=path.relative_to(self.root).as_posix())
            elif decision.get("approval_source") in {"user", "delegated_policy"} and not self._approval_ref_resolves(decision.get("approval_ref")):
                self.add("WRK015", "blocking", "approval reference cannot be corroborated from a local source", item_id, path=path.relative_to(self.root).as_posix())
            elif decision.get("approval_source") == "unverified":
                self.add("WRK015", "blocking", "approval is explicitly unverified", item_id, path=path.relative_to(self.root).as_posix())

    def _check_lifecycle(self, item_id: str, data: dict[str, Any], row: dict[str, str], text: str, path: Path) -> None:
        status = row["status"]
        rel = path.relative_to(self.root).as_posix()
        if status in {"ready", "in_progress", "in_review", "done"}:
            if is_placeholder(data.get("authorization_ref")):
                self.add("WRK003", "blocking", "ready work needs an explicit authorization source", item_id, path=rel)
            if not isinstance(data.get("accepted_criteria_commit"), str) or not isinstance(data.get("implementation_base_commit"), str):
                self.add("WRK003", "blocking", "ready work needs accepted criteria and implementation base refs", item_id, path=rel)
            for heading in ("## Outcome", "## Scope", "## Execution checkpoint"):
                match = re.search(rf"{re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)", text, re.S)
                body = match.group(1).strip() if match else ""
                if is_placeholder(body):
                    self.add("WRK014", "blocking", f"{heading[3:]} must be concrete before readiness/completion", item_id, path=rel)
        if status in {"in_progress", "in_review", "done"}:
            if row["owner"] == "unassigned":
                self.add("WRK003", "blocking", "active work needs a named owner", item_id, path="roadmap.md")
            for dep in row.get("depends_on_ids", []):
                if self.roadmap.get(dep, {}).get("status") != "done":
                    self.add("WRK004", "blocking", f"required dependency {dep} is not done", item_id, path="roadmap.md")
        if status == "blocked":
            blocker = data.get("blocker")
            if not isinstance(blocker, dict) or is_placeholder(blocker.get("reason")) or is_placeholder(blocker.get("next_action")):
                self.add("WRK003", "blocking", "blocked status needs structured reason and next_action", item_id, path=rel)
        if status in {"deferred", "cancelled"}:
            disposition = data.get("disposition")
            if not isinstance(disposition, dict) or any(is_placeholder(disposition.get(k)) for k in ("reason", "approval_ref", "evidence")) or disposition.get("approval_source") not in {"user", "delegated_policy"} or not self._approval_ref_resolves(disposition.get("approval_ref")):
                self.add("WRK015", "blocking", "deferred/cancelled status needs reason and inspectable disposition authority", item_id, path=rel)

    def _changed_since(self, commit: str, watch: list[str]) -> set[str]:
        if not valid_commit(self.root, commit):
            return set()
        names = git(self.root, "diff", "--name-only", f"{commit}..{self.head_sha}", check=False).splitlines()
        if self.dirty:
            names += git(self.root, "diff", "--name-only", check=False).splitlines()
            names += git(self.root, "ls-files", "--others", "--exclude-standard", check=False).splitlines()
        normalized = {n.replace("\\", "/") for n in names if n}
        return {name for name in normalized if any(fnmatch.fnmatch(name, pat) for pat in watch)}

    def _input_fingerprint(self, watch: list[str]) -> str:
        tracked = git(self.root, "ls-files", "-co", "--exclude-standard").splitlines()
        selected = sorted(
            name.replace("\\", "/") for name in tracked
            if any(fnmatch.fnmatch(name.replace("\\", "/"), pattern) for pattern in watch)
        )
        digest = hashlib.sha256()
        for name in selected:
            candidate = self.root / name
            if candidate.is_file():
                digest.update(name.encode("utf-8"))
                digest.update(b"\0")
                digest.update(candidate.read_bytes())
                digest.update(b"\0")
        return digest.hexdigest()

    def _record_metadata_only_since(self, commit: str, paths: set[str], item_id: str, current_text: str) -> set[str]:
        """Exclude post-run record bookkeeping after the final read-only check is repeated."""
        remaining = set(paths)
        if "roadmap.md" in remaining:
            before_text = git(self.root, "show", f"{commit}:roadmap.md", check=False)
            before_rows, _ = parse_roadmap(before_text) if before_text else ({}, [])
            current_rows, _ = parse_roadmap((self.root / "roadmap.md").read_text(encoding="utf-8"))
            mutable = {"status", "owner", "next_action", "line"}
            def stable_rows(rows: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
                return {key: {field: value for field, value in row.items() if field not in mutable} for key, row in rows.items()}
            if stable_rows(before_rows) == stable_rows(current_rows):
                remaining.discard("roadmap.md")

        record_rel = f"work/{item_id}.md"
        if record_rel in remaining:
            before = git(self.root, "show", f"{commit}:{record_rel}", check=False)
            old_data, _, old_error = parse_frontmatter(before)
            new_data, _, new_error = parse_frontmatter(current_text)
            if not old_error and not new_error and old_data is not None and new_data is not None:
                for data in (old_data, new_data):
                    data.pop("evidence", None)
                    data.pop("reviews", None)
                def stable_body(record: str) -> str:
                    _, _, body = parse_frontmatter(record)
                    for heading in ("## Execution checkpoint", "## Evidence", "## Review"):
                        body = re.sub(rf"{re.escape(heading)}\s*\n.*?(?=\n## |\Z)", heading + "\n<mutable>\n", body, flags=re.S)
                    return body.strip()
                if old_data == new_data and stable_body(before) == stable_body(current_text):
                    remaining.discard(record_rel)

        remaining = {name for name in remaining if not name.startswith("work/reviews/")}
        return remaining

    def _check_evidence(self, item_id: str, data: dict[str, Any], path: Path) -> None:
        status = self.roadmap[item_id]["status"]
        historical_done = status == "done" and (self.done_commits.get(item_id) != self.head_sha or self.dirty)
        rel = path.relative_to(self.root).as_posix()
        required = {c.get("id") for c in data.get("criteria", []) if isinstance(c, dict) and c.get("required") is True}
        entries = data.get("evidence", []) if isinstance(data.get("evidence"), list) else []
        covered: set[str] = set()
        for ev in entries:
            if not isinstance(ev, dict):
                self.add("WRK007", "blocking", "evidence must be an object", item_id, path=rel)
                continue
            cid = ev.get("criterion_id")
            if cid not in required:
                self.add("WRK007", "blocking", f"evidence references non-required/unknown criterion {cid}", item_id, str(cid) if cid else None, rel)
                continue
            check = self.checks.get(ev.get("check_id"))
            review_method = self.review_methods.get(ev.get("check_id"))
            if check is None and review_method is None:
                self.add("WRK007", "blocking", f"unknown configured check ID {ev.get('check_id')}", item_id, cid, rel)
                continue
            source_commit = ev.get("source_commit")
            fingerprint = ev.get("source_fingerprint")
            if bool(source_commit) == bool(fingerprint):
                self.add("WRK008", "blocking", "evidence needs exactly one source commit or fingerprint", item_id, cid, rel)
                continue
            watch = check.get("watched_paths", []) if check is not None else []
            stale_paths: set[str] = set()
            historical_stale = False
            if source_commit:
                if not valid_commit(self.root, source_commit):
                    self.add("WRK016", "unable", "evidence source commit cannot be resolved", item_id, cid, rel)
                    continue
                stale_paths = self._changed_since(source_commit, watch)
                if check is not None and check.get("id") == "record-integrity":
                    stale_paths = self._record_metadata_only_since(source_commit, stale_paths, item_id, (self.root / rel).read_text(encoding="utf-8"))
                historical_stale = status == "done" and bool(stale_paths)
                if stale_paths:
                    if historical_done:
                        self.add("WRK008", "warning", f"historical evidence remains recorded; current assurance is stale for: {', '.join(sorted(stale_paths))}", item_id, cid, rel)
                    else:
                        self.add("WRK008", "missing", f"evidence is stale for changed configured inputs: {', '.join(sorted(stale_paths))}", item_id, cid, rel)
                        continue
            elif not (isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
                self.add("WRK008", "blocking", "source_fingerprint must be a SHA-256 hex digest", item_id, cid, rel)
                continue
            else:
                if fingerprint != self._input_fingerprint(watch):
                    historical_stale = historical_done
                    severity = "warning" if historical_stale else "missing"
                    self.add("WRK008", severity, "working-tree input fingerprint does not match the current configured inputs", item_id, cid, rel)
                    if not historical_stale:
                        continue

            expected_argv = check.get("argv", []) if check is not None else []
            if ev.get("command") != expected_argv:
                severity = "warning" if historical_done else "blocking"
                self.add("WRK007", severity, "recorded command differs from the current configured argv", item_id, cid, rel)
            if ev.get("result") not in RESULTS or ev.get("provenance") not in PROVENANCE or not isinstance(ev.get("applicable"), bool):
                self.add("WRK007", "blocking", "evidence result, provenance, or applicability is invalid", item_id, cid, rel)
                continue
            if review_method is not None and (ev.get("provenance") != "agent_reported" or ev.get("exit_status") is not None):
                self.add("WRK007", "blocking", "structured-review evidence must be agent_reported with no command exit status", item_id, cid, rel)
            if ev.get("criteria_baseline_commit") != data.get("accepted_criteria_commit"):
                severity = "warning" if status == "done" and data.get("accepted_criteria_commit") != ev.get("criteria_baseline_commit") else "blocking"
                self.add("WRK008", severity, "evidence criteria baseline does not match the accepted baseline", item_id, cid, rel)
            if ev.get("result") != "pass" or ev.get("applicable") is not True or ev.get("exit_status") not in (0, None):
                severity = "warning" if historical_done else "missing" if status == "in_review" else "blocking"
                self.add("WRK008", severity, f"criterion evidence is not an applicable successful result ({ev.get('result')})", item_id, cid, rel)
                continue
            if check is not None and check.get("test_expectation"):
                discovered, selected, skipped = (ev.get("discovered_tests"), ev.get("selected_tests"), ev.get("skipped_tests"))
                if not all(isinstance(n, int) and n >= 0 for n in (discovered, selected, skipped)):
                    self.add("WRK007", "missing", "configured test evidence needs discovered/selected/skipped counts", item_id, cid, rel)
                    continue
                minimum = int(check.get("minimum_discovered", 1))
                if discovered < minimum or selected < minimum or skipped != 0:
                    severity = "warning" if historical_done and skipped == 0 else "blocking"
                    self.add("WRK011", severity, f"test discovery/selection/skips differ from current rule (discovered={discovered}, selected={selected}, skipped={skipped})", item_id, cid, rel)
                    if severity == "blocking":
                        continue
            covered.add(cid)
        missing = required - covered
        if missing:
            severity = "warning" if historical_done else "missing" if status == "in_review" else "blocking"
            for cid in sorted(missing):
                self.add("WRK007", severity, "required criterion has no fresh applicable passing evidence", item_id, cid, rel)

    def _check_reviews(self, item_id: str, data: dict[str, Any], path: Path) -> None:
        rel = path.relative_to(self.root).as_posix()
        baseline = data.get("accepted_criteria_commit")
        done_at = self.done_commits.get(item_id, self.head_sha)
        historical_done = done_at != self.head_sha or self.dirty
        try:
            procedure = (self.root / "work" / "review-procedure.md").read_text(encoding="utf-8")
        except OSError:
            procedure = ""
        rubric_match = re.search(r"(?m)^Rubric version: `([a-z0-9-]+)`\s*$", procedure)
        current_rubric = rubric_match.group(1) if rubric_match else None
        valid_ready = False
        unresolved_review_findings: set[str] = set()
        for review in data.get("reviews", []) if isinstance(data.get("reviews"), list) else []:
            if not isinstance(review, dict):
                continue
            if review.get("role") not in REVIEW_ROLES or review.get("verdict") not in REVIEW_VERDICTS:
                self.add("WRK009", "blocking", "review role or verdict is invalid", item_id, path=rel)
                continue
            report = review.get("report")
            if is_placeholder(report):
                self.add("WRK009", "missing", "review report reference is missing", item_id, path=rel)
            else:
                parsed_report = urlsplit(str(report))
                report_path = (self.root / str(report)).resolve()
                if parsed_report.scheme == "https":
                    pass
                elif parsed_report.scheme or self.root not in report_path.parents or not report_path.is_file():
                    self.add("WRK009", "missing", f"review report does not resolve as repository path or HTTPS URL: {report}", item_id, path=rel)
            revision = review.get("assessed_source_commit")
            if not valid_commit(self.root, revision) or not valid_commit(self.root, review.get("criteria_baseline_commit")):
                self.add("WRK009", "unable", "review revision or criteria baseline is unresolved", item_id, path=rel)
                continue
            if review.get("criteria_baseline_commit") != baseline:
                self.add("WRK009", "blocking", "review must cover the accepted criteria baseline", item_id, path=rel)
            if not current_rubric or review.get("rubric_version") != current_rubric:
                severity = "warning" if historical_done else "blocking"
                self.add("WRK009", severity, "review rubric differs from the current rubric; inspect historical completion or repeat review", item_id, path=rel)
            later = git(self.root, "diff", "--name-only", f"{revision}..{done_at}", check=False).splitlines()
            allowed_bookkeeping = {"roadmap.md", rel}
            if any(p.replace("\\", "/") not in allowed_bookkeeping and not p.replace("\\", "/").startswith("work/reviews/") for p in later):
                self.add("WRK009", "blocking", "review assessed an older revision with substantive changes afterward", item_id, path=rel)
            after_done = git(self.root, "diff", "--name-only", f"{done_at}..{self.head_sha}", check=False).splitlines()
            if after_done or (self.dirty and self.changed_paths):
                self.add("WRK009", "warning", "historical completion and review remain recorded; inspect current changes before making a new completion claim", item_id, path=rel)
            if review.get("role") in {"author", "self"}:
                self.add("WRK009", "blocking", "self-review cannot satisfy independent review", item_id, path=rel)
            if review.get("verdict") == "changes_required":
                findings = review.get("findings", [])
                unresolved_review_findings.update(x for x in findings if isinstance(x, str))
            if review.get("role") in {"independent", "domain_owner"} and review.get("verdict") == "ready" and not review.get("findings"):
                valid_ready = True
        if not valid_ready:
            self.add("WRK009", "missing", "done requires an independent/domain-owner review with verdict ready", item_id, path=rel)
        resolutions = data.get("resolutions", []) if isinstance(data.get("resolutions"), list) else []
        resolved_ids = {r.get("finding_id") for r in resolutions if isinstance(r, dict) and r.get("disposition") == "resolved" and not is_placeholder(r.get("evidence"))}
        unresolved = unresolved_review_findings - resolved_ids
        if unresolved:
            self.add("WRK013", "blocking", f"review findings lack explicit resolution evidence: {', '.join(sorted(unresolved))}", item_id, path=rel)

    def _check_parent_completion(self) -> None:
        for parent_id, row in self.roadmap.items():
            if row["status"] != "done":
                continue
            for child_id, child_row in self.roadmap.items():
                child_data = self.items.get(child_id, (None, "", None))[0]
                if child_data is None or parent_id not in child_row.get("parent_ids", []):
                    continue
                if child_data.get("completion_disposition") == "optional" or child_row["status"] == "done":
                    continue
                disp = child_data.get("disposition")
                disposition_ok = child_row["status"] in {"deferred", "cancelled"} and isinstance(disp, dict) and self._approval_ref_resolves(disp.get("approval_ref"))
                if not disposition_ok:
                    self.add("WRK006", "blocking", f"parent cannot be done while required child {child_id} is {child_row['status']}", parent_id, path="roadmap.md")

    def _check_changed_paths(self) -> None:
        tests = sorted(p for p in self.changed_paths if TEST_PATH.search(p))
        enforcement = sorted(p for p in self.changed_paths if p in ENFORCEMENT_PATHS or p.startswith(".github/workflows/"))
        if tests:
            self.add("WRK011", "review", f"test/fixture/expected-output paths changed; inspect behavior and selection: {', '.join(tests)}", path="roadmap.md")
        if enforcement:
            self.add("WRK012", "review", f"verification/checker/review/CI enforcement changed; require review against accepted rules: {', '.join(enforcement)}", path="roadmap.md")


def validate(root: Path, base_ref: str | None = None, focus_id: str | None = None) -> dict[str, Any]:
    return Checker(root, base_ref, focus_id).run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only project work-record checker")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-ref", help="Git ref for status/path comparison; defaults to WORK_BASE_REF or main")
    parser.add_argument("--work-id", help="Focus display on an item (global integrity checks still run)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    result = validate(args.root, args.base_ref, args.work_id)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"work check: {result['outcome']}")
        if result["findings"]:
            for finding in result["findings"]:
                where = ":" + finding["path"] if finding.get("path") else ""
                item = f" [{finding['work_id']}]" if finding.get("work_id") else ""
                criterion = f" ({finding['criterion_id']})" if finding.get("criterion_id") else ""
                print(f"{finding['rule_id']} {finding['severity']}{item}{criterion}{where}: {finding['message']}")
        else:
            print("No findings.")
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
