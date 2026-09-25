# W-000 interim independent review

- Work item: W-000
- Verdict: `changes_required`
- Proposed revision assessed: `deae9144aaf0f0443bdd3a2455ec4058d5a62c25`
- Accepted criteria commit: `66229f901bfa1cdf1bbbcd7260c7f368c64f3ce1`
- Rubric version: `review-rubric-v1`
- Reviewer role: `independent`
- Model (if available): `gpt-6-astra`
- Reasoning effort (if available): `xhigh`
- Primary evidence/provenance inspected: source-level inspection of `scripts/check_work.py`; the prior PR run `36087613798` reported 10/10 fixtures passing, but did not cover the cases below.

## Findings

| Finding ID | Criterion | File/evidence location | Severity | Finding | Resolution evidence |
|---|---|---|---|---|---|
| W-000-R1 | W-000-AC2 | `scripts/check_work.py`: `parse_roadmap`, `_check_transition_snapshot`, `_check_parent_completion_at_commit` | blocking | Historical roadmap snapshots did not include parsed parent/dependency IDs. Transition and required-child checks could therefore miss an invalid earlier status even if the dependency or child later became complete. | Pending fix review. |
| W-000-R2 | W-000-AC2 | `scripts/check_work.py`: `_history_evidence_complete` | blocking | Historical completion checks did not verify that configured inputs stayed fresh from the evidence source revision through the `in_review`/`done` transition revision. | Pending fix review. |
| W-000-R3 | W-000-AC2 | `scripts/check_work.py`: `_check_criteria_baseline` | blocking | The current editable `accepted_criteria_commit` pointer was trusted. Moving it to a revision containing edited criteria could suppress decision coverage against the originally accepted wording. | Pending fix review. |
| W-000-R4 | W-000-AC2 | `scripts/check_work.py`: `_record_metadata_only_since` | blocking | The helper treated `parse_frontmatter`'s error string as Markdown body text. Successful parses returned an empty string, so scope/prose changes could be misclassified as bookkeeping and avoid staling evidence. | Pending fix review. |

## Rationale and limits

This is an interim report, not a completed review of all W-000 criteria. The independent reviewer confirmed the four blocking source-level findings above, then could not finish the rubric inspection because its usage allowance was exhausted. The original CI run passed 10 discovered/selected fixtures with no skips, but those fixtures did not cover these cases. A fresh reviewer must assess the fixes and the complete proposed revision before W-000 can be marked done.
