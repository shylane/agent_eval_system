# Work record policy — schema version 1

## Format

Each roadmap-linked work file starts with `---`, one JSON object, `---`, then Markdown. The checker rejects duplicate keys, missing/unknown fields, malformed types, unknown schema versions, invalid links, and unresolved placeholders in readiness/completion fields. It does not infer structure from prose and has no YAML dependency.

Top-level keys are exactly those listed in [work/README.md](README.md). Allowed values:

- `kind`: `milestone | feature | task | experiment`; `completion_disposition`: `required | optional`.
- `evidence.result`: `pass | fail | skipped | not_discovered | unable_to_verify`; `provenance`: `agent_reported | runner_observed | trusted_ci`; `applicable` is boolean.
- `decisions.change_type`: `clarify | strengthen | relax | remove | add`; `approval_source`: `user | delegated_policy | not_required | unverified`.
- `resolutions.disposition`: `resolved | open`.
- `reviews.verdict`: `ready | changes_required | unable_to_verify`; `role`: `independent | domain_owner | author | self`.
- Commit references are full immutable 40- or 64-character object IDs. Moving branch names are not baselines. `accepted_criteria_commit` contains the accepted criterion wording; `implementation_base_commit` is the implementation starting snapshot and may equal the criteria commit.

Criterion shape: `{id, required, behavior, verification_method}`. IDs are unique/stable `<work-id>-AC<n>`.

Evidence shape: `{criterion_id, source_commit, source_fingerprint, criteria_baseline_commit, check_id, command, exit_status, result, applicable, summary, location, provenance, environment, discovered_tests, selected_tests, skipped_tests}`. Exactly one source locator is non-null. `command` is an argv array actually executed. Test counts can be null only where the configured check has no test-selection concept.

Decision shape: `{affected_criteria, previous_wording, proposed_wording, change_type, reason, supporting_evidence, user_impact, verification_impact, approval_source, approval_ref}`. Any accepted criterion edit/replacement needs one. Keep IDs stable; replacement gets a new ID and records old removal/new addition. A material relaxation/removal needs an inspectable user/delegated approval source; an agent-written approval field is not corroboration.

Resolution shape: `{finding_id, disposition, evidence, approval_ref}`. A resolution does not erase the original finding or turn a failed check into a pass.

Review shape: `{role, assessed_source_commit, criteria_baseline_commit, rubric_version, verdict, report, model, reasoning_effort, findings}`. Use null for unavailable model/effort. Reviewer model/effort choices are configurable in [reviewer-config.json](reviewer-config.json); never silently substitute a weaker unavailable reviewer.

`blocker` is null or `{reason,next_action}`. `disposition` is null or `{reason,approval_source,approval_ref,evidence}` and is mandatory for `deferred`/`cancelled`.

## Links and hierarchy

IDs match `W-` plus at least three digits. Each roadmap row has exactly one file. `parent` describes scope; `depends_on` describes order; each graph is acyclic and refers to existing IDs. `ledger_refs` contains valid experiment IDs. Work-file local links and evidence/review locations must resolve.

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

Normal path is `proposed -> ready -> in_progress -> in_review -> done`. Any active state may move to blocked/deferred/cancelled; blocked may resume at the appropriate active state; in_review may return to in_progress for fixes; deferred may return to proposed with a new decision. Done and cancelled are terminal; create corrective work instead of erasing history. The checker inspects Git status history.

Before substantive implementation record accepted criteria, implementation base, and authorization. Existing explicit user instructions count; do not ask twice. Routine choices within accepted scope need no repeated approval. Optional work does not start automatically after required work.

Accepted scope changes record affected IDs, old/new wording, reason/evidence, type, user impact, verification impact, and approval source. Implementers may propose but cannot approve their own material reduction. AI review is recommendation, not product authority. If source is uncorroborated, preserve uncertainty and seek the decision while continuing independent work.

## Evidence, freshness, and review

The committed [verification.json](../verification.json) is the only command configuration executed. Work-item prose is never executed. Evidence names work/criterion IDs, exact commit or input fingerprint, criteria baseline, check ID/config and actual argv, exit status/result, summary/location, provenance, and environment. A commit does not describe dirty files.

`agent_reported` is a claim. `runner_observed` means the configured command was launched and observed; its report is editable and not tamper-proof. `trusted_ci` identifies an exact CI checkout/artifact. State only the assurance actually available. A successful exit is insufficient when no required tests were discovered/selected or required tests were skipped.

Relevant code, criteria, tests/fixtures/expected outputs/selection/skips, dependencies, verification config, checker, review rubric, or CI changes invalidate affected evidence for a new completion claim. The checker flags changed paths mechanically; whether a test was weakened is a human/model judgment. Later code does not erase historical completion; current assurance is separate. Bookkeeping-only changes do not rerun expensive behavior checks.

Review the accepted criteria baseline, decisions, code and test diffs, primary evidence, provenance, and enforcement changes. Use a fresh read-only reviewer where practical; don't execute candidate scripts as trusted reviewer instructions. Verdicts are `ready`, `changes_required`, or `unable_to_verify`. Keep one review and one fix review per checkpoint. A recommendation is not merge permission.

Use `codex/` branches and isolated worktrees for substantive implementation where supported. Worktrees are not security boundaries. Separate parallel ownership; one integration owner reconciles roadmap and ID collisions. Commit coherent checkpoints with work IDs. Do not rewrite history or include unrelated changes. This setup grants no push/merge/publish/hosted-settings authority beyond explicit user instruction.

Run inexpensive checks after record edits and before completion; optional local hooks can be bypassed. PR CI and manual milestone checks are prepared in `.github/workflows`; deep review is for substantive completion, material scope/enforcement changes, and review fixes, not every commit. CI uses read-only permissions and no secrets. Candidate code/tests execute code, so CI remains isolated. A changed checker cannot approve itself; review against the prior accepted rules. Rerun affected checks after integration changes.

## Migration

The checker supports version 1 only. Migrate explicitly in a deliberate commit: preserve prior record/evidence, retain IDs for unchanged behavior, record replacements, transform fields, then validate. Never silently reinterpret an unknown version.
