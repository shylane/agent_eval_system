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

## Empty values and links

- In JSON, use `null` for an unknown scalar reference, `[]` for no array entries, and `null` for no blocker/disposition. Do not use empty strings or infer missing facts from prose.
- In the roadmap, `—` means no parent or dependencies; dependency IDs are comma-separated. Use `unassigned` for no owner.
- Roadmap links use `[title](work/W-###.md)`. Parent/dependency fields contain IDs. `ledger_refs` contains existing IDs such as `E7` and should link to the ledger in the body. Local Markdown links are relative; external links use HTTPS.
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
