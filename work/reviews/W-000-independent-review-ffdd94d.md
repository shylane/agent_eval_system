# Independent review report

- Work item: W-000
- Verdict: `changes_required`
- Proposed source: `ffdd94d8ef093c4d0dc0a199999912f491373cb5`
- Accepted criteria baseline: `66229f901bfa1cdf1bbbcd7260c7f368c64f3ce1`
- Implementation base: `875de8daf87934166fc805c059836b9ae2068771`
- Rubric: `review-rubric-v1`
- Reviewer role: `independent`
- Model and effort: `gpt-6-astra`, `high` (dispatch metadata)
- Primary evidence: full implementation diff, accepted criteria, checker/runner/fixtures/configuration/policy/procedures/templates/skill/AGENTS/CI, prior review reports, and exact CI artifact [project-verification.json](W-000-ci-ffdd94d/project-verification.json).

## Findings

| Finding ID | Criteria | Location | Severity | Finding | Resolution evidence |
|---|---|---|---|---|---|
| W-000-R12 | W-000-AC2, W-000-AC3 | `scripts/check_work.py`, working-tree done handling, `_check_evidence`, `_check_reviews`; `.githooks/pre-commit`; `scripts/test_work_checker.py` | Blocking | A new uncommitted `in_review → done` transition can pass with stale/missing evidence and an outdated review. The working-tree history path assigned HEAD as the completion commit. Because the checkout was dirty, evidence was treated as historical and stale/missing coverage became warnings; review freshness compared only the reviewed commit with HEAD, omitting local changes. A valid committed `in_review` record with a ready review of HEAD, a locally changed watched test, and an uncommitted done status can therefore pass. Require a committed done snapshot or otherwise assess the exact working tree, and cover valid local completion, missing/stale evidence, and substantive changes after review. | Pending fix and review. |

## Previous findings and criteria

R1–R2 are addressed in historical roadmap/evidence checks and their dependency and freshness fixtures. R3–R4 remain fixed through immutable acceptance-anchor checks and strict body parsing. R5–R6 remain fixed through substantive review freshness checks and structured-review bookkeeping. R7 is addressed by allowing a resolved historical changes-required report before a fresh ready review, while a later changes-required report supersedes readiness. R8 is addressed by selecting latest evidence per criterion/check and exercising refreshed evidence through a committed done transition. R9 is addressed for post-merge history: the checker recovers the done commit already in the comparison base, and the fixture commits later code/rubric changes. R10 is addressed by checking unresolved findings from the done snapshot; late resolution cannot repair it. R11 is addressed by including index-only changes in changed-path/freshness checks and staging a watched test in its regression.

AC1 appears satisfied by the authoritative records, exact schema, lifecycle, evidence/decision rules, templates, and examples. AC2 remains incomplete because of R12. AC3 covers the requested fixture categories, but does not cover the uncommitted completion path. AC4 appears satisfied by the repository skill, AGENTS pointers, review procedure/report, configured checks, optional hook, and read-only PR/manual workflow. AC5 remains aligned with the project decision record: W-001 and W-002 are proposed, with pilot selection and E7 baseline research unresolved. W-000 accepted criteria are unchanged.

The exact CI artifact identifies source `ffdd94d8ef093c4d0dc0a199999912f491373cb5`, record-integrity exit 0, 22 discovered/selected fixtures, zero skips, Linux, Python 3.12.14, uv 0.9.16, and a clean checkout. Its output includes WRK011/WRK012 review notices. The artifact was inspected locally; this reviewer did not independently authenticate its hosted origin.

Review was static and read-only; no candidate scripts or tests ran and no files were changed. R12 follows from source inspection, not a newly executed reproduction. This is a recommendation only; it does not authorize completion, merge, or product-scope changes.
