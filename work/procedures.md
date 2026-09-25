# Work item operations

## Create

**Inputs:** requested outcome, relevant manifest/ledger decision, parent/dependency IDs, and execution authority.

1. Search the roadmap and nearby records for overlap.
2. Keep hypotheses/results in the experiment ledger. Add a linked item only when execution needs scheduling.
3. As integration owner, allocate the next unused `W-###`; never reuse IDs.
4. Copy [TEMPLATE.md](TEMPLATE.md); define scope, criteria/methods, and ledger links.
5. Add one roadmap row. Unapproved work is `proposed`, refs are null, owner is `unassigned`, and next action is concrete.
6. Run `uv run --no-project python scripts/check_work.py`.

**Success:** one linked unique item with clear authority and criteria or explicitly preserved uncertainty. **Failure:** merge overlap into an existing item or leave unknown authority proposed.

## Resume

**Inputs:** work ID and checkout.

1. Read its roadmap row and detailed record; inspect parent/required children, dependencies, accepted baseline, decisions, evidence and blocker.
2. Check Git status, branch/worktree owner, last relevant commits, and whether evidence inputs changed.
3. Use `Execution checkpoint` and next action; re-run only checks made stale by relevant changes.
4. If blocked, record the concrete obstacle and next action. Continue independent authorized work.

**Success:** state governing criteria/baseline, last checkpoint, evidence freshness, and next action. **Failure:** missing baseline or authority stays explicit; escalate only the dependent decision.

## Amend

**Inputs:** affected criterion IDs, old/new wording, reason/evidence, user/verification impacts, and approval source when required.

1. Compare current criteria with immutable `accepted_criteria_commit`.
2. Add every field in the policy decision shape before changing accepted wording.
3. Implementers may propose but cannot approve their own material relaxation/removal. AI review is a recommendation.
4. If meaning or approval is unclear, keep the change unresolved and ask the user; continue independent work.
5. Re-run affected checks after acceptance; preserve historical evidence.

**Success:** the accepted decision and fresh evidence are recorded. **Failure:** retain accepted wording and mark the proposed change unverified.

## Complete

**Inputs:** candidate source revision, accepted baseline, criterion evidence, configured check outputs, reviewer availability.

1. Confirm the item is `in_progress`, source is identified, and no scope change is unaccepted.
2. Run the read-only checker, then relevant commands from `verification.json` via `scripts/run_verification.py`; never execute item prose.
3. Confirm all required criteria have applicable passing evidence; required tests were discovered/selected with no skips; blocking findings have explicit resolutions.
4. Set `in_review` and request a fresh independent review using [review-procedure.md](review-procedure.md). Inspect primary evidence.
5. Append the report and review object in chronological order; preserve earlier entries. Resolve every blocking finding with evidence. A later `changes_required` or `unable_to_verify` entry supersedes any earlier ready recommendation; review fixes once.
6. Mark `done` only when checker prerequisites pass and the latest review entry is `ready`, independent/domain-owner, finding-free, and fresh for the proposed revision. Otherwise remain `in_review` or `blocked` with a next action.

**Success:** fresh applicable evidence plus ready independent review. **Failure:** missing/stale/unable evidence, skipped tests, uncorroborated approval, or open findings means not done. A negative experiment result passes if the agreed method/reporting contract passed.
