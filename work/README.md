# Project work records

## Start a session

1. Read the repository [README](../README.md) and this contract.
2. Read [roadmap.md](../roadmap.md); do not load every work record.
3. Open only the selected item's linked `work/W-*.md`. Read relevant manifest sections, experiment IDs, and prior decisions/evidence as needed.
4. Use `$project-work` for create, resume, amend, or complete; detailed steps and examples are in [procedures](procedures.md) and [examples](examples.md).
5. If authority, scope, or evidence is unclear, record the uncertainty and ask the user/reviewer only for the dependent decision. Continue independent authorized work.

## Authority and format

- [manifest.md](../manifest.md): product purpose, principles, boundaries, and committed direction.
- [experiments.md](../experiments.md): hypotheses, methods, results, and research decisions.
- [roadmap.md](../roadmap.md): priority, status, parent, dependencies, owner, and next action.
- `work/W-*.md`: detailed scope, stable criteria, execution checkpoint, scope decisions, evidence, and review references.

Work items use Markdown with a JSON object between the first pair of `---` lines, followed by Markdown. JSON is strict and parsed with Python's standard library. The checker reads explicit fields only; prose cannot supply omitted values. Exact version-1 schema and lifecycle are in [policy.md](policy.md); [TEMPLATE.md](TEMPLATE.md) is canonical.

Required JSON keys: `schema_version`, `id`, `kind`, `authorization_ref`, `accepted_criteria_commit`, `implementation_base_commit`, `completion_disposition`, `ledger_refs`, `criteria`, `evidence`, `decisions`, `resolutions`, `reviews`, `blocker`, and `disposition`. `schema_version` is integer `1`. `kind`: `milestone | feature | task | experiment`; `completion_disposition`: `required | optional`. Each criterion has stable ID `<work-id>-AC<n>`, boolean `required`, `behavior`, and `verification_method`.

Nested fields are exact: evidence `{criterion_id, source_commit, source_fingerprint, criteria_baseline_commit, check_id, command, exit_status, result, applicable, summary, location, provenance, environment, discovered_tests, selected_tests, skipped_tests}`; decision `{affected_criteria, previous_wording, proposed_wording, change_type, reason, supporting_evidence, user_impact, verification_impact, approval_source, approval_ref}`; resolution `{finding_id, disposition, evidence, approval_ref}`; review `{role, assessed_source_commit, criteria_baseline_commit, rubric_version, verdict, report, model, reasoning_effort, findings}`. `blocker` is null or `{reason,next_action}`; `disposition` is null or `{reason,approval_source,approval_ref,evidence}`. See [policy.md](policy.md) for the field types and null rules.

`verification.json` has `schema_version: 1`, `checks`, and `review_methods`. A command check has exactly `{id, argv, test_expectation, minimum_discovered, watched_paths}` plus optional `timeout_seconds` or `kind: "command"`; `argv` is a nonempty string array and never a shell expression. A review method has exactly `{id, procedure, report_template, required_reviewer_role}` and is a documented, non-executable procedure. `reviewer-config.json` has exactly `{schema_version, preferred_model, reasoning_effort, required_reviewer_role, fallback}`; null model/effort means no preference is set.

`accepted_criteria_commit` is the fixed acceptance anchor from initial authorization. Never move it to conceal later wording changes; record later accepted amendments as decisions against that anchor. `implementation_base_commit` separately records the implementation starting snapshot.

## Empty values and links

- In JSON, use `null` for an unknown scalar reference, `[]` for no array entries, and `null` for no blocker/disposition. Do not use empty strings or infer missing facts from prose.
- In the roadmap, `—` means no parent or dependencies; dependency IDs are comma-separated. Use `unassigned` for no owner.
- Roadmap links use `[title](work/W-###.md)`. Parent/dependency fields contain IDs. `ledger_refs` contains existing IDs such as `E7` and should link to the ledger in the body. Local Markdown links are relative; external links use HTTPS.
- `source_commit`, `source_fingerprint`, `authorization_ref`, decision wording, and approval/report references use null only when unknown or inapplicable; do not use empty strings. Evidence/report paths are repository-root-relative. Exactly one of `source_commit` and `source_fingerprint` is populated. A missing approval source remains null or `unverified`; a made-up reference is never a valid approval.
- Do not duplicate mutable roadmap fields in work files.

## Small work

Do not create an item for every question or trivial edit. Minor corrections can belong to an existing item when they do not change accepted behavior, scope, or verification rules. Research remains in the ledger; create a linked item only when execution needs scheduling.

## Completion gate

`done` requires applicable, successful, fresh evidence for every required criterion; required tests discovered and selected with no required skips; explicit resolution of blocking review findings; and a required review with verdict `ready` covering the proposed implementation revision and accepted baseline. A negative experiment finding can satisfy the work contract when the agreed method and reporting criteria passed. A review recommendation does not authorize merge.

Before proposing completion, run:

```powershell
uv run --no-project python scripts/check_work.py
uv run --no-project python scripts/run_verification.py --check record-integrity --check checker-fixtures
```

The checker is read-only. The runner executes only commands in [verification.json](../verification.json); it writes a report only when passed `--report <path>`. Checks run after management-record changes and before completion. Local hooks are optional and bypassable. CI is prepared for pull requests and manual milestone checks; this does not mean hosted required checks or branch protections are enabled.

To opt into the local pre-commit hook, run `git config --local core.hooksPath .githooks`. It is advisory and can be bypassed; for example, use `git -c core.hooksPath=/dev/null commit` in Git Bash or `git -c core.hooksPath=NUL commit` in Windows PowerShell. The pull-request workflow uses read-only repository permission, does not persist checkout credentials, and stores its report as an exact-revision artifact. Configure it as a required check only after review and approval.

## Checker findings

Machine output contains `outcome`, `exit_code`, optional `focused_work_id`, and findings with `rule_id`, `severity`, `work_id`, `criterion_id`, `path`, and `message`. Stable rules are:

| Rule | Mechanical finding |
|---|---|
| WRK001 | Record/config schema, required fields, types, or allowed values |
| WRK002 | Work-item IDs and repository links |
| WRK003 | Lifecycle status, transition, authorization, or active owner |
| WRK004 | Missing/invalid parent, dependency, experiment, or focus ID |
| WRK005 | Parent/dependency cycle or self-parent |
| WRK006 | Parent completion with unfinished required child |
| WRK007 | Criterion/evidence coverage and evidence references |
| WRK008 | Evidence success, applicability, baseline, or freshness |
| WRK009 | Review report, assessed revision, role, or verdict |
| WRK010 | Accepted-criteria change decision record |
| WRK011 | Required test discovery/selection/skips or changed test paths to inspect |
| WRK012 | Changed checker/review/CI enforcement paths to inspect |
| WRK013 | Unresolved review finding |
| WRK014 | Placeholder or missing concrete outcome/scope/checkpoint/roadmap action |
| WRK015 | Uncorroborated material approval or missing disposition |
| WRK016 | Unable to resolve Git or immutable revision context |

Severity `blocking` yields `failure`/exit 1; `missing` yields `missing_evidence`/exit 2; `unable` yields `unable_to_check`/exit 3. `review` and `warning` require inspection but do not by themselves claim a mechanical failure. Exit 0 is `passed`.
