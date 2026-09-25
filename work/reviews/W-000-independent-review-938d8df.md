# Independent review report

- Work item: W-000
- Verdict: `changes_required`
- Proposed revision assessed: `938d8dfd6575fdcfc72a5b6ef8e40b00a52366af`
- Accepted criteria commit: `66229f901bfa1cdf1bbbcd7260c7f368c64f3ce1`
- Implementation base: `875de8daf87934166fc805c059836b9ae2068771`
- Rubric version: `review-rubric-v1`
- Reviewer role: `independent`
- Model: `gpt-6-astra` (dispatch metadata)
- Reasoning effort: `high` (dispatch metadata)
- Primary evidence/provenance inspected: accepted and current W-000 criteria; implementation changes from the supplied base; checker, runner, fixtures, configuration, workflow, hook, policy, procedures, templates, skill and agent pointers; earlier R1–R10 review reports; exact-revision [CI artifact](W-000-ci-938d8df/project-verification.json).

## Findings

| Finding ID | Criterion | File/evidence location | Severity | Finding | Resolution evidence |
|---|---|---|---|---|---|
| W-000-R9 | W-000-AC2, W-000-AC3 | `scripts/check_work.py`, `_check_history` and `_check_reviews`; `scripts/test_work_checker.py`, historical rubric fixture | Blocking; previous finding remains partially unresolved | Historical completion is preserved only when its transition falls after the selected comparison base. `_check_history` searches `base..HEAD`, so an item already done in `main`/`origin/main` has no recovered `done_commits` entry. `_check_reviews` then substitutes HEAD for its completion revision. A subsequent committed rubric or substantive change is consequently treated as preceding completion, producing a rubric mismatch or blocking stale-review finding against a valid historical completion. This affects ordinary subsequent work after merge. The rubric regression keeps `main` at the proposed seed and changes the rubric only in the working tree, so it misses this case. Recover the actual historical completion independently of the change-comparison range, and test committed later changes with completion already in the base. | Pending fix. The candidate fixes the original branch-history case, but not this baseline-contained completion case. |
| W-000-R11 | W-000-AC2, W-000-AC3 | `scripts/check_work.py`, `_git_setup` and `_changed_since`; `.githooks/pre-commit`; `scripts/test_work_checker.py` | Blocking | Staged changes are omitted from local freshness and changed-path detection. Both collectors combine committed changes with plain `git diff --name-only` and untracked files; neither includes changes present only in the index. After passing evidence is recorded, editing and staging a watched test/source file leaves the working tree dirty but removes that file from the collected changes. An `in_review` item can therefore retain apparently fresh evidence, and the pre-commit checker can miss the changed test/enforcement path. Include staged changes or compare HEAD with the working tree, and add a regression that stages a watched modification before checking. | Pending. Current freshness fixtures use unstaged edits or committed changes; they do not cover this path. |

## Rationale and limits

AC1 appears satisfied: the dashboard, exact record schema, authority boundaries, lifecycle, dependencies, decisions and evidence rules are documented and supported by templates. W-000’s accepted criteria remain unchanged.

AC2 and AC3 remain incomplete because of the findings above. R1–R8 and R10 have corresponding source changes and meaningful regression coverage. In particular:

- Evidence supersession selects the latest row per criterion/check while preserving previous rows. The refreshed-evidence regression proceeds through a committed `done` transition; stale latest evidence still blocks.
- Historical changes-required reviews can precede a fresh ready review with explicit resolutions. A later changes-required review supersedes readiness.
- Transition-time resolution checking reads the done snapshot. The late-resolution fixture verifies that a later resolution cannot repair that transition.
- R9’s new fixture validates one historical-rubric case, but does not cover completion already present in the comparison baseline.

The synthetic reports, counts and behavior files appropriately test the record checker rather than claim product results. The requested fixture categories are represented, and the fixture count increase does not conceal a reduction in accepted behavior. However, those tests do not establish the two paths identified above.

AC4 otherwise appears satisfied: the skill, agent pointers, review procedure/report, explicit command configuration, optional hook and PR/manual workflow exist. The workflow checks out the candidate revision, uses read-only repository permissions, disables persisted checkout credentials and uploads an artifact named for that revision. Hosted branch protections were not verified.

AC5 appears satisfied: W-001 and W-002 remain proposed, with null authorization and baseline references, and preserve the unresolved workflow and E7 baseline choices in README, manifest and the experiment ledger.

The exact-revision artifact identifies `938d8dfd6575fdcfc72a5b6ef8e40b00a52366af`, reports record-integrity exit 0 and 20 discovered/selected fixtures with zero skips, and records Linux, Python 3.12.14, uv 0.9.16 and a clean source tree. The artifact was inspected locally; this reviewer did not independently authenticate its hosted CI origin.

This review was static and read-only. No candidate scripts or tests were executed and no files were changed. The findings follow from source inspection, not newly executed reproductions. This is a recommendation only; it does not approve completion, merge or scope changes.
