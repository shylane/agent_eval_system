# Independent review report

- Work item: W-000
- Verdict: `changes_required`
- Proposed source: `dd568ec92df0912a484febb80775c5ade4830ecc`
- Accepted criteria baseline: `66229f901bfa1cdf1bbbcd7260c7f368c64f3ce1`
- Implementation base: `875de8daf87934166fc805c059836b9ae2068771`
- Rubric: `review-rubric-v1`
- Reviewer role: `independent`
- Model and effort: `gpt-6-astra`, `high` (dispatch metadata)
- Primary evidence: accepted criteria; complete source diff; checker, fixtures, verification configuration, policy, runner, workflow, skill and prior findings; exact CI artifact [project-verification.json](W-000-ci-dd568ec/project-verification.json).

## Findings

| Finding ID | Criteria | Location | Severity | Finding | Resolution evidence |
|---|---|---|---|---|---|
| W-000-R14 | W-000-AC2, W-000-AC3 | `scripts/check_work.py`, `_check_evidence`; `scripts/test_work_checker.py` | Blocking | Historical evidence still uses the current definition when its ID remains configured. Changing a completed non-test check to require test counts makes its valid null counters trigger a missing-evidence finding. Use the completion-time definition for the historical claim even when the ID remains, report changed current rules separately, and preserve the requirement for fresh counters on new work. Add regression coverage for both cases. | Pending fix and review. |

## Criteria and prior findings

R12 is resolved by blocking an uncommitted `done` transition and checking staged/unstaged paths for evidence and review freshness. R13 is resolved: the checker recovers the completion-time catalog for retired or renamed IDs, and the fixture checks command and review-method renames after completion plus a blocking unknown ID on new work.

R1–R11 fixes remain present. AC1, AC4, and AC5 appear satisfied. AC2 and AC3 remain incomplete because R14 is not covered. W-001/W-002 remain proposed, preserving the unresolved workflow choice and E7 baseline research.

The exact CI artifact identifies `dd568ec92df0912a484febb80775c5ade4830ecc`, record-integrity exit 0, and 24 discovered/selected fixtures with zero skips or failures, Linux, Python 3.12.14, and uv 0.9.16. It was downloaded from GitHub Actions run 36100825325 and inspected; the reviewer did not independently authenticate hosted CI.

Review was static and read-only. No candidate scripts or tests were executed and no files were changed. This recommendation does not authorize completion, merge, or product-scope changes.
