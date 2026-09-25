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

from check_work import frontmatter_body, parse_frontmatter, validate


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
    return data, frontmatter_body(text)


def write_record(root: Path, data: dict[str, Any], body: str, item_id: str = "W-900") -> None:
    text = "---\n" + json.dumps(data, indent=2) + "\n---\n" + body
    (root / "work" / f"{item_id}.md").write_text(text, encoding="utf-8")


def update_roadmap_row(root: Path, item_id: str, *, status: str | None = None,
                       parent: str | None = None, depends_on: str | None = None) -> None:
    path = root / "roadmap.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"| {item_id} | "):
            cells = [part.strip() for part in line.strip().strip("|").split("|")]
            if status is not None:
                cells[3] = status
            if parent is not None:
                cells[4] = parent
            if depends_on is not None:
                cells[5] = depends_on
            lines[index] = "| " + " | ".join(cells) + " |"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"missing roadmap row {item_id}")


class FixtureRepo:
    """Construct an isolated synthetic history with a proposed item and a valid completion."""

    def __init__(self, final_status: str = "done", integrity_watches_work: bool = False,
                 structured_review: bool = False, historical_review: bool = False,
                 resolve_historical_review: bool = True):
        self.temp = tempfile.TemporaryDirectory(prefix="work-record-fixture-")
        self.root = Path(self.temp.name)
        shutil.copytree(FIXTURE, self.root, dirs_exist_ok=True)
        if integrity_watches_work or structured_review:
            config_path = self.root / "verification.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if structured_review:
                config["review_methods"] = [{
                    "id": "structured-review-v1",
                    "procedure": "work/structured-review-procedure.md",
                    "report_template": "work/structured-review-template.md",
                    "required_reviewer_role": "independent",
                }]
                (self.root / "work" / "structured-review-procedure.md").write_text(
                    "Synthetic fixture review method.\n", encoding="utf-8"
                )
                (self.root / "work" / "structured-review-template.md").write_text(
                    "Synthetic fixture report template.\n", encoding="utf-8"
                )
            config["checks"][0]["watched_paths"].extend(["roadmap.md", "work/**"])
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
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
            "summary": "Twenty-two required synthetic fixture tests were discovered, selected, and passed.",
            "location": "case.json",
            "provenance": "runner_observed",
            "environment": "isolated temporary Git repository; Python stdlib",
            "discovered_tests": 22,
            "selected_tests": 22,
            "skipped_tests": 0,
        }
        data, body = read_record(self.root)
        data["evidence"] = [self.evidence.copy()]
        write_record(self.root, data, body)
        if final_status in {"in_review", "done"}:
            if structured_review:
                review_report = self.root / "work" / "reviews" / "W-900-structured-review.md"
                review_report.parent.mkdir(parents=True, exist_ok=True)
                review_report.write_text(
                    f"# Synthetic structured review\n\nSource: `{self.source_commit}`\n\n"
                    "Synthetic fixture evidence only.\n",
                    encoding="utf-8",
                )
                review_evidence = {
                    "criterion_id": "W-900-AC1",
                    "source_commit": self.source_commit,
                    "source_fingerprint": None,
                    "criteria_baseline_commit": self.criteria_baseline,
                    "check_id": "structured-review-v1",
                    "command": [],
                    "exit_status": None,
                    "result": "pass",
                    "applicable": True,
                    "summary": "The synthetic review method completed its report.",
                    "location": "work/reviews/W-900-structured-review.md",
                    "provenance": "agent_reported",
                    "environment": "synthetic isolated fixture; structured review method",
                    "discovered_tests": None,
                    "selected_tests": None,
                    "skipped_tests": None,
                }
                data, body = read_record(self.root)
                data["evidence"].append(review_evidence)
                write_record(self.root, data, body)
            self.set_status("in_review", "fixture-agent", "Request synthetic independent review")
            self.commit("synthetic in review")
            self.review_revision = git(self.root, "rev-parse", "HEAD")
        if final_status == "done":
            if historical_review:
                self.record_prior_changes_review(resolve=resolve_historical_review)
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
        data["reviews"].append({
            "role": "independent",
            "assessed_source_commit": self.review_revision,
            "criteria_baseline_commit": self.criteria_baseline,
            "rubric_version": "review-rubric-v1",
            "verdict": "ready",
            "report": "work/reviews/W-900-review.md",
            "model": None,
            "reasoning_effort": None,
            "findings": [],
        })
        write_record(self.root, data, body)
        self.set_status("done", "fixture-agent", "Preserve the historical result")
        self.commit("synthetic done")

    def record_prior_changes_review(self, *, resolve: bool = True) -> None:
        report = self.root / "work" / "reviews" / "W-900-changes-required.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            f"# Synthetic changes-required review\n\nRevision: `{self.criteria_baseline}`\n\n"
            "Finding W-900-R1 was fixed in a later implementation checkpoint.\n",
            encoding="utf-8",
        )
        data, body = read_record(self.root)
        data["reviews"].append({
            "role": "independent",
            "assessed_source_commit": self.criteria_baseline,
            "criteria_baseline_commit": self.criteria_baseline,
            "rubric_version": "review-rubric-v1",
            "verdict": "changes_required",
            "report": "work/reviews/W-900-changes-required.md",
            "model": None,
            "reasoning_effort": None,
            "findings": ["W-900-R1"],
        })
        if resolve:
            data["resolutions"].append({
                "finding_id": "W-900-R1",
                "disposition": "resolved",
                "evidence": "Synthetic implementation checkpoint fixes the reported issue.",
                "approval_ref": None,
            })
        write_record(self.root, data, body)
        self.commit("synthetic resolved review finding")

    def append_prior_resolution(self) -> None:
        data, body = read_record(self.root)
        data["resolutions"].append({
            "finding_id": "W-900-R1",
            "disposition": "resolved",
            "evidence": "Synthetic post-transition resolution; it cannot repair the historical done snapshot.",
            "approval_ref": None,
        })
        write_record(self.root, data, body)
        self.commit("synthetic late review finding resolution")

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

    def test_structured_review_evidence_stays_fresh_and_substantive_edits_stale_it(self) -> None:
        complete = FixtureRepo(structured_review=True)
        try:
            result = validate(complete.root, "main")
            self.assertEqual(result["exit_code"], 0, result)
            self.assertFalse([f for f in result["findings"] if f["severity"] in {"blocking", "missing", "unable"}], result)
        finally:
            complete.close()

        stale = FixtureRepo("in_review", structured_review=True)
        try:
            behavior = stale.root / "src" / "behavior.txt"
            behavior.write_text(behavior.read_text(encoding="utf-8") + "substantive change\n", encoding="utf-8")
            result = validate(stale.root, "main")
            self.assertTrue(
                any("src/behavior.txt" in f["message"] for f in findings(result, "WRK008")),
                result,
            )
        finally:
            stale.close()

    def test_resolved_historical_review_precedes_current_ready_review(self) -> None:
        repo = FixtureRepo(historical_review=True)
        try:
            data, body = read_record(repo.root)
            self.assertEqual([review["verdict"] for review in data["reviews"]], ["changes_required", "ready"])
            result = validate(repo.root, "main")
            self.assertEqual(result["exit_code"], 0, result)
            self.assertFalse(findings(result, "WRK013"), result)
        finally:
            repo.close()

        unresolved = FixtureRepo(historical_review=True)
        try:
            data, body = read_record(unresolved.root)
            data["resolutions"] = []
            write_record(unresolved.root, data, body)
            unresolved.commit("synthetic unresolved review finding")
            result = validate(unresolved.root, "main")
            self.assertTrue(findings(result, "WRK013"), result)
        finally:
            unresolved.close()

        later_changes_required = FixtureRepo()
        try:
            report = later_changes_required.root / "work" / "reviews" / "W-900-later-changes-required.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("# Synthetic later changes-required review\n", encoding="utf-8")
            data, body = read_record(later_changes_required.root)
            data["reviews"].append({
                "role": "independent",
                "assessed_source_commit": later_changes_required.review_revision,
                "criteria_baseline_commit": later_changes_required.criteria_baseline,
                "rubric_version": "review-rubric-v1",
                "verdict": "changes_required",
                "report": "work/reviews/W-900-later-changes-required.md",
                "model": None,
                "reasoning_effort": None,
                "findings": ["W-900-R2"],
            })
            data["resolutions"].append({
                "finding_id": "W-900-R2",
                "disposition": "resolved",
                "evidence": "Synthetic fixture records the reported correction.",
                "approval_ref": None,
            })
            write_record(later_changes_required.root, data, body)
            later_changes_required.commit("synthetic later changes-required report")
            result = validate(later_changes_required.root, "main")
            self.assertTrue(
                any("latest recorded review" in f["message"] for f in findings(result, "WRK009")),
                result,
            )
        finally:
            later_changes_required.close()

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
        for discovered, selected, skipped in ((13, 13, 1), (0, 0, 0)):
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

    def test_completion_already_in_base_preserves_historical_assurance(self) -> None:
        repo = FixtureRepo()
        try:
            git(repo.root, "switch", "main")
            git(repo.root, "merge", "--ff-only", "fixture-work")
            git(repo.root, "switch", "-c", "post-completion-followup")
            with (repo.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# committed regression check after historical completion\n")
            procedure = repo.root / "work" / "review-procedure.md"
            procedure.write_text(
                procedure.read_text(encoding="utf-8").replace("review-rubric-v1", "review-rubric-v2"),
                encoding="utf-8",
            )
            repo.commit("synthetic follow-up after completion was merged")
            result = validate(repo.root, "main")
            self.assertTrue(
                any("historical completion used rubric review-rubric-v1" in finding["message"]
                    for finding in findings(result, "WRK009")), result,
            )
            self.assertFalse(
                [finding for finding in result["findings"] if finding["severity"] in {"blocking", "missing", "unable"}],
                result,
            )
        finally:
            repo.close()

    def test_rubric_change_does_not_rewrite_historical_completion(self) -> None:
        repo = FixtureRepo()
        try:
            procedure = repo.root / "work" / "review-procedure.md"
            text = procedure.read_text(encoding="utf-8")
            procedure.write_text(text.replace("review-rubric-v1", "review-rubric-v2"), encoding="utf-8")
            result = validate(repo.root, "main")
            self.assertTrue(
                any("historical completion used rubric review-rubric-v1" in finding["message"]
                    for finding in findings(result, "WRK009")), result,
            )
            self.assertFalse(
                [finding for finding in result["findings"] if finding["severity"] in {"blocking", "missing", "unable"}],
                result,
            )
        finally:
            repo.close()

    def test_fresh_evidence_supersedes_stale_history_but_stale_latest_blocks(self) -> None:
        refreshed = FixtureRepo("in_review")
        try:
            original, _ = read_record(refreshed.root)
            previous = original["evidence"][0].copy()
            with (refreshed.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# changed input before refreshed evidence\n")
            refreshed.commit("synthetic evidence input changed")
            data, body = read_record(refreshed.root)
            data["evidence"].append(previous.copy())
            data["evidence"][-1]["source_commit"] = git(refreshed.root, "rev-parse", "HEAD")
            write_record(refreshed.root, data, body)
            refreshed.commit("synthetic fresh evidence appended")
            result = validate(refreshed.root, "main")
            current = read_record(refreshed.root)[0]
            self.assertEqual(current["evidence"][0], previous)
            self.assertEqual(len(current["evidence"]), 2)
            self.assertTrue(any("superseded by a later result" in finding["message"]
                                for finding in findings(result, "WRK008")), result)
            self.assertFalse([finding for finding in result["findings"]
                              if finding["severity"] in {"blocking", "missing", "unable"}], result)
            refreshed.review_revision = git(refreshed.root, "rev-parse", "HEAD")
            refreshed.finish_review()
            result = validate(refreshed.root, "main")
            roadmap = (refreshed.root / "roadmap.md").read_text(encoding="utf-8")
            self.assertIn("| W-900 | [Synthetic negative experiment](work/W-900.md) | P1 | done |", roadmap)
            self.assertFalse([finding for finding in result["findings"]
                              if finding["severity"] in {"blocking", "missing", "unable"}], result)
        finally:
            refreshed.close()

        stale = FixtureRepo("in_review")
        try:
            original, _ = read_record(stale.root)
            previous = original["evidence"][0].copy()
            with (stale.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# changed input before a stale latest result\n")
            stale.commit("synthetic evidence input changed")
            data, body = read_record(stale.root)
            data["evidence"].append(previous.copy())
            write_record(stale.root, data, body)
            stale.commit("synthetic stale latest evidence appended")
            result = validate(stale.root, "main")
            self.assertTrue(findings(result, "WRK008"), result)
            self.assertTrue([finding for finding in result["findings"]
                             if finding["severity"] in {"missing", "blocking"}], result)
        finally:
            stale.close()

    def test_resolution_added_after_done_does_not_repair_transition(self) -> None:
        repo = FixtureRepo(historical_review=True, resolve_historical_review=False)
        try:
            repo.append_prior_resolution()
            result = validate(repo.root, "main")
            self.assertTrue(
                any("done transition lacked explicit resolution evidence" in finding["message"]
                    for finding in findings(result, "WRK013")), result,
            )
        finally:
            repo.close()

    def test_substantive_item_edit_after_review_invalidates_review(self) -> None:
        repo = FixtureRepo("in_review")
        try:
            record_path = repo.root / "work" / "W-900.md"
            record = record_path.read_text(encoding="utf-8")
            record = record.replace(
                "Included: temporary version-1 records, controlled fixture mutations, and assertions on checker findings.",
                "Included: expanded behavior beyond the scope assessed by the reviewer.",
            )
            record_path.write_text(record, encoding="utf-8")
            repo.commit("synthetic scope edit after review")

            # Record fresh evidence for the changed inputs while deliberately keeping
            # the earlier review revision to verify that completion still rejects it.
            data, body = read_record(repo.root)
            data["evidence"][0]["source_commit"] = git(repo.root, "rev-parse", "HEAD")
            write_record(repo.root, data, body)
            repo.commit("synthetic refreshed evidence")
            repo.finish_review()

            result = validate(repo.root, "main")
            self.assertTrue(
                any("review assessed an older revision with substantive changes afterward" in f["message"] for f in findings(result, "WRK009")),
                result,
            )
        finally:
            repo.close()

    def test_stale_inputs_block_the_historical_in_review_transition(self) -> None:
        repo = FixtureRepo("in_progress")
        try:
            with (repo.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# changed before the review transition\n")
            repo.set_status("in_review", "fixture-agent", "Request review with stale inputs")
            repo.commit("synthetic stale in-review transition")
            result = validate(repo.root, "main")
            self.assertTrue(
                any("in_review transition lacked complete fresh evidence" in f["message"] for f in findings(result, "WRK007")),
                result,
            )
        finally:
            repo.close()

    def test_staged_watched_input_invalidates_local_evidence(self) -> None:
        repo = FixtureRepo("in_review")
        try:
            with (repo.root / "tests" / "test_behavior.py").open("a", encoding="utf-8") as handle:
                handle.write("# staged watched input must invalidate evidence\n")
            git(repo.root, "add", "tests/test_behavior.py")
            self.assertEqual(git(repo.root, "diff", "--name-only"), "")
            self.assertEqual(git(repo.root, "diff", "--cached", "--name-only"), "tests/test_behavior.py")
            result = validate(repo.root, "main")
            self.assertTrue(
                any(finding["rule_id"] == "WRK008" and finding["severity"] == "missing"
                    and "tests/test_behavior.py" in finding["message"] for finding in result["findings"]),
                result,
            )
            self.assertTrue(
                any("tests/test_behavior.py" in finding["message"] for finding in findings(result, "WRK011")),
                result,
            )
        finally:
            repo.close()

    def test_historical_dependency_and_required_child_are_checked(self) -> None:
        dependency = FixtureRepo("in_progress")
        try:
            self.add_child(dependency.root, parent="—")
            update_roadmap_row(dependency.root, "W-900", status="in_review", depends_on="W-901")
            dependency.commit("synthetic start before dependency completion")
            update_roadmap_row(dependency.root, "W-901", status="done")
            dependency.commit("synthetic later dependency completion")
            result = validate(dependency.root, "main")
            self.assertTrue(
                any("transition started before dependency W-901" in f["message"] for f in findings(result, "WRK004")),
                result,
            )
        finally:
            dependency.close()

        parent = FixtureRepo("in_progress")
        try:
            self.add_child(parent.root, parent="W-900")
            update_roadmap_row(parent.root, "W-900", status="in_review")
            parent.commit("synthetic parent enters review")
            update_roadmap_row(parent.root, "W-900", status="done")
            parent.commit("synthetic parent completes before required child")
            update_roadmap_row(parent.root, "W-901", status="done")
            parent.commit("synthetic later child completion")
            result = validate(parent.root, "main")
            self.assertTrue(
                any("parent was completed while required child W-901 remained unfinished" in f["message"] for f in findings(result, "WRK006")),
                result,
            )
        finally:
            parent.close()

    def test_accepted_criteria_anchor_cannot_be_moved_to_hide_an_edit(self) -> None:
        repo = FixtureRepo("in_progress")
        try:
            data, body = read_record(repo.root)
            data["criteria"][0]["behavior"] = "Replace the agreed comparison with an unsupported success claim."
            write_record(repo.root, data, body)
            repo.commit("synthetic criteria edit")
            changed_criteria_commit = git(repo.root, "rev-parse", "HEAD")
            data, body = read_record(repo.root)
            data["accepted_criteria_commit"] = changed_criteria_commit
            write_record(repo.root, data, body)
            repo.commit("synthetic attempt to move accepted baseline")
            result = validate(repo.root, "main")
            self.assertTrue(
                any("immutable acceptance anchor" in f["message"] for f in findings(result, "WRK010")),
                result,
            )
        finally:
            repo.close()

    def test_scope_prose_change_is_not_record_bookkeeping(self) -> None:
        repo = FixtureRepo("in_review", integrity_watches_work=True)
        try:
            data, body = read_record(repo.root)
            check = next(check for check in json.loads((repo.root / "verification.json").read_text(encoding="utf-8"))["checks"] if check["id"] == "record-integrity")
            data["evidence"][0].update({
                "check_id": "record-integrity", "command": check["argv"],
                "discovered_tests": None, "selected_tests": None, "skipped_tests": None,
            })
            edited_body = body.replace("Included: temporary version-1 records, controlled fixture mutations, and assertions on checker findings.",
                                       "Included: a widened synthetic behavior beyond the accepted fixture.")
            write_record(repo.root, data, edited_body)
            result = validate(repo.root, "main")
            self.assertTrue(findings(result, "WRK008"), result)
        finally:
            repo.close()

    @staticmethod
    def add_child(root: Path, *, parent: str) -> None:
        child = {
            "schema_version": 1, "id": "W-901", "kind": "task", "authorization_ref": None,
            "accepted_criteria_commit": None, "implementation_base_commit": None,
            "completion_disposition": "required", "ledger_refs": [],
            "criteria": [{"id": "W-901-AC1", "required": True, "behavior": "Complete the child task", "verification_method": "Inspect the fixture state"}],
            "evidence": [], "decisions": [], "resolutions": [], "reviews": [], "blocker": None, "disposition": None,
        }
        body = "\n# Child task\n\n## Outcome\nComplete the synthetic child.\n\n## Scope\nIncluded: synthetic state.\n\nExcluded: product behavior.\n\n## Acceptance criteria\nStructured fixture criterion.\n\n## Execution checkpoint\nNot started.\n\n## Decisions and changes\nNone.\n\n## Evidence\nNone.\n\n## Review\nNone.\n"
        write_record(root, child, body, "W-901")
        roadmap = root / "roadmap.md"
        text = roadmap.read_text(encoding="utf-8")
        roadmap.write_text(text + f"| W-901 | [Required child](work/W-901.md) | P2 | proposed | {parent} | — | unassigned | Define fixture scope |\n", encoding="utf-8")

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
