# Work record policy — schema version 1

## Format

Each roadmap-linked work file starts with `---`, one JSON object, `---`, then Markdown. The checker rejects duplicate keys, missing/unknown fields, malformed types, unknown schema versions, invalid links, and unresolved placeholders in readiness/completion fields. It does not infer structure from prose and has no YAML dependency.

Top-level keys are exactly those listed in [work/README.md](README.md): `schema_version`, `id`, `kind`, `authorization_ref`, `accepted_criteria_commit`, `implementation_base_commit`, `completion_disposition`, `ledger_refs`, `criteria`, `evidence`, `decisions`, `resolutions`, `reviews`, `blocker`, and `disposition`. No top-level or nested extra keys are allowed. `schema_version` is the integer `1` (not a string or boolean). Allowed values:

- `kind`: `milestone | feature | task | experiment`; `completion_disposition`: `required | optional`.
- `evidence.result`: `pass | fail | skipped | not_discovered | unable_to_verify`; `provenance`: `agent_reported | runner_observed | trusted_ci`; `applicable` is boolean.
- `decisions.change_type`: `clarify | strengthen | relax | remove | add`; `approval_source`: `user | delegated_policy | not_required | unverified`.
- `resolutions.disposition`: `resolved | open`.
- `reviews.verdict`: `ready | changes_required | unable_to_verify`; `role`: `independent | domain_owner | author | self`.
- Commit references are full immutable 40- or 64-character object IDs. Moving branch names are not baselines. `accepted_criteria_commit` contains the accepted criterion wording; `implementation_base_commit` is the implementation starting snapshot and may equal the criteria commit.

Criterion shape is exactly `{id, required, behavior, verification_method}`. IDs are unique/stable `<work-id>-AC<n>`.

Evidence shape is exactly `{criterion_id, source_commit, source_fingerprint, criteria_baseline_commit, check_id, command, exit_status, result, applicable, summary, location, provenance, environment, discovered_tests, selected_tests, skipped_tests}`. Exactly one source locator is non-null. For an executable check, `check_id` and `command` match `verification.json`, and the argv was actually executed. For a documented review method, `check_id` names a `review_methods` entry, `command` is `[]`, `exit_status` is null, and provenance is `agent_reported`; link its report. Test counts are null only where the configured executable check has no test-selection concept or the evidence is a review method.

Decision shape is exactly `{affected_criteria, previous_wording, proposed_wording, change_type, reason, supporting_evidence, user_impact, verification_impact, approval_source, approval_ref}`. `affected_criteria` is a nonempty list of stable IDs. Wording, reason, supporting evidence, and both impacts are concrete strings. `previous_wording` is null only for `add`; `proposed_wording` is null only for `remove`. `approval_ref` is null when no approval is claimed. Any accepted criterion edit/replacement needs one. Keep IDs stable; replacement gets a new ID and records old removal/new addition. A material relaxation/removal needs an inspectable user/delegated approval source; an agent-written approval field is not corroboration.

Resolution shape is exactly `{finding_id, disposition, evidence, approval_ref}`. `finding_id` and `evidence` are concrete strings; `approval_ref` is null when no separate approval applies. A resolution does not erase the original finding or turn a failed check into a pass.

Review shape is exactly `{role, assessed_source_commit, criteria_baseline_commit, rubric_version, verdict, report, model, reasoning_effort, findings}`. `findings` is an array of stable finding references; `model` and `reasoning_effort` are null only when unavailable. Reviewer model/effort choices are configurable in [reviewer-config.json](reviewer-config.json); never silently substitute a weaker unavailable reviewer. Review and evidence `location` paths are repository-root-relative and must resolve locally; HTTPS artifact/report links are allowed for human retrieval.

`blocker` is null or exactly `{reason,next_action}`. `disposition` is null or exactly `{reason,approval_source,approval_ref,evidence}` and is mandatory for `deferred`/`cancelled`; its reason/evidence are concrete strings and approval must be attributable to the user or delegated policy.

## Links and hierarchy

IDs match `W-` plus at least three digits. Roadmap priority is `P0 | P1 | P2 | P3`; status uses the lifecycle values below; an empty owner is written `unassigned`. Each roadmap row has exactly one Markdown link in the form `[title](work/W-###.md)`. Parent contains one ID or `—`; `depends_on` contains comma-separated IDs or `—`. Parent describes scope; dependencies describe order; each graph is acyclic and refers to existing IDs. `ledger_refs` contains valid experiment IDs. Work-file local links and evidence/review locations must resolve.

Children are required unless `completion_disposition` is `optional`. A parent cannot be done while a required child is unfinished unless that child is deferred/cancelled with explicit reason and corroborated disposition. Required dependencies must be done before a dependent enters `in_progress`, `in_review`, or `done`.

## Lifecycle

Statuses: `proposed | ready | in_progress | in_review | done | blocked | deferred | cancelled`.

- `proposed`: consideration only; implementation not authorized.
- `ready`: authorization source, clear scope/criteria/methods/dependencies, and immutable criteria/base refs exist.
- `in_progress`: named owner executes ready work.
- `in_review`: completion proposed and required evidence available; review may be pending.
- `done`: all required evidence is applicable, fresh, successful; no required tests are skipped/undiscovered; blocking findings resolved; required review is `ready`.
- `blocked`: concrete obstacle and next action in both structured record and roadmap.
- `deferred`/`cancelled`: reason and disposition decision recorded. Removing/cancelling required child scope needs explicit accepted disposition.

Permitted transitions (remaining in the same state is allowed):

| From | To |
|---|---|
| New ID | proposed |
| proposed | ready, blocked, deferred, cancelled |
| ready | in_progress, blocked, deferred, cancelled |
| in_progress | in_review, blocked, deferred, cancelled |
| in_review | done, in_progress, blocked, deferred, cancelled |
| blocked | in_progress, in_review, deferred, cancelled |
| deferred | proposed, cancelled |
| done | none |
| cancelled | none |

`ready` needs authorization, clear scope/criteria/methods, and immutable criteria/base refs in the transition commit. `in_progress` needs a named owner and completed required dependencies. `in_review` needs passing evidence for every required criterion. `done` needs the same evidence plus a ready required review and no unfinished required children. `blocked` needs a concrete reason and next action. `deferred`/`cancelled` need disposition evidence and attributable authority. Returning from `deferred` to `proposed` adds a new decision. Done and cancelled are terminal; create corrective work instead of erasing history. The checker inspects the Git status history and validates transition-time prerequisites.

Before substantive implementation record accepted criteria, implementation base, and authorization. Existing explicit user instructions count; do not ask twice. Routine choices within accepted scope need no repeated approval. Optional work does not start automatically after required work.

Accepted scope changes record affected IDs, old/new wording, reason/evidence, type, user impact, verification impact, and approval source. Implementers may propose but cannot approve their own material reduction. AI review is recommendation, not product authority. If source is uncorroborated, preserve uncertainty and seek the decision while continuing independent work.

## Evidence, freshness, and review

The committed [verification.json](../verification.json) is the only command configuration executed; its `review_methods` catalog points to structured human/model procedures that are not executed as commands. Work-item prose is never executed. An evidence object has exactly the fields in the evidence shape above. It names the work/criterion ID, exactly one immutable `source_commit` or SHA-256 `source_fingerprint`, criteria baseline, configured check or review-method ID and actual argv (empty for reviews), integer/null exit status, result/applicability, concrete summary/location, provenance, environment, and test counts. Test counts may be null only when that configured command has no test-selection concept or evidence is a review. A commit does not describe dirty files.

`agent_reported` is a claim. `runner_observed` means the configured command was launched and observed; its report is editable and not tamper-proof. `trusted_ci` identifies an exact CI checkout/artifact. State only the assurance actually available. A successful exit is insufficient when no required tests were discovered/selected or required tests were skipped.

Relevant code, accepted criteria, dependencies, tests/fixtures/expected outputs/selection/skips, verification config, checker, review rubric, or CI changes invalidate affected evidence for a new completion claim. The checker flags changed paths mechanically; whether a test was weakened is a human/model judgment. Later code does not erase historical completion; current assurance is separate. Bookkeeping-only changes do not rerun expensive behavior checks. For `record-integrity` evidence, changes limited to roadmap status/owner/next action, the same item's evidence/review fields and execution checkpoint, and files under `work/reviews/` are treated as report bookkeeping; rerun the inexpensive checker after those updates so the submitted claims themselves are assessed. Changes to accepted scope, criteria, decisions, dependencies, or other records still make evidence stale.

Review the accepted criteria baseline, decisions, code and test diffs, primary evidence, provenance, and enforcement changes. Use a fresh read-only reviewer where practical; don't execute candidate scripts as trusted reviewer instructions. Verdicts are `ready`, `changes_required`, or `unable_to_verify`. Keep one review and one fix review per checkpoint. A recommendation is not merge permission.

Use `codex/` branches and isolated worktrees for substantive implementation where supported. Worktrees are not security boundaries. Separate parallel ownership; one integration owner reconciles roadmap and ID collisions. Commit coherent checkpoints with work IDs. Do not rewrite history or include unrelated changes. This setup grants no push/merge/publish/hosted-settings authority beyond explicit user instruction.

Run inexpensive checks after record edits and before completion; optional local hooks can be bypassed. PR CI and manual milestone checks are prepared in `.github/workflows`; deep review is for substantive completion, material scope/enforcement changes, and review fixes, not every commit. CI uses read-only permissions and no secrets. Candidate code/tests execute code, so CI remains isolated. A changed checker cannot approve itself; review against the prior accepted rules. Rerun affected checks after integration changes.

## Migration

The checker supports version 1 only. Migrate explicitly in a deliberate commit: preserve prior record/evidence, retain IDs for unchanged behavior, record replacements, transform fields, then validate. Never silently reinterpret an unknown version.
