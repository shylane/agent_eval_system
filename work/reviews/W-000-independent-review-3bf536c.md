# W-000 independent review: candidate 3bf536c

## Assessment

- Work item: W-000
- Verdict: `changes_required`
- Reviewer role: `independent`
- Assessed source commit: `3bf536c2391e9f395137aaf18c3ae81ba074dd13`
- Accepted criteria baseline: `66229f901bfa1cdf1bbbcd7260c7f368c64f3ce1`
- Implementation base: `875de8daf87934166fc805c059836b9ae2068771`
- Rubric: `review-rubric-v1`
- Model and effort: unavailable in this invocation

## Blocking finding

**W-000-R15 — AC2 and AC3:** malformed JSON field types could still raise uncaught `TypeError` exceptions, preventing the checker from returning stable findings or valid JSON output.

The first fix guarded enum membership and identifier hashing, but left `criteria` consumers that assumed an array. A record with `criteria: null` or a scalar could fail in `_criteria_map`, `_check_evidence`, or `_history_evidence_complete`. Historical verification catalogs also iterated `checks` and `review_methods` without validating their array and entry shapes; malformed historical count/path values could flow into later comparisons. The review recommended guarding these consumers, failing closed on malformed historical configuration, and extending the regression fixtures.

## Other criteria

R12–R14 appeared addressed in the inspected source and their focused regression cases. AC1, AC4, and AC5 appeared satisfied. AC2/AC3 remained incomplete pending the R15 fixes.

The exact-revision CI report for `3bf536c` is at [project-verification.json](W-000-ci-3bf536c/project-verification-3bf536c2391e9f395137aaf18c3ae81ba074dd13/project-verification.json). It passed 26 discovered/selected fixtures with zero skips and failures, but did not cover the malformed criteria collections or historical catalog cases identified here.

## Follow-up

The finding was fixed in `910f9157edbf5702fab98150cd650fb76a4b46fb`. The final independent fix review is recorded in [W-000-fix-review-910f915.md](W-000-fix-review-910f915.md), and exact-source CI evidence is in [the 910f915 report](W-000-ci-910f915/project-verification-910f9157edbf5702fab98150cd650fb76a4b46fb/project-verification.json).

## Review limits

This was a separate static, read-only review. No candidate scripts or tests were executed, no files were edited, and the hosted CI origin was not independently authenticated by the reviewer. The report is a recommendation and grants no completion, merge, or scope-change authority.
