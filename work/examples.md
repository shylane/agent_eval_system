# Compact examples

These are synthetic operating examples, not new project commitments. Use [TEMPLATE.md](TEMPLATE.md)'s same JSON-frontmatter field names.

## New proposed feature

Search for overlap, allocate the next unused ID, and create a `proposed` row with null authorization/baseline refs. Add exact scope and stable methods. Example criterion: `{"id":"W-123-AC1","required":true,"behavior":"A user can export the reviewed report as JSON","verification_method":"Round-trip schema check and privacy review"}`. Proposal does not authorize implementation.

## Child task

Use a parent ID in roadmap; set `completion_disposition` to `required` unless scope is explicitly optional. Put ordering under `Depends on`, not `Parent`. An unfinished required child blocks parent completion without an explicit accepted disposition.

## Experiment linked to implementation

Keep hypothesis/method/result in the experiment ledger and put its ID (for example `"ledger_refs": ["E7"]`) in the item. Research and implementation remain separate records. A negative finding may satisfy a research contract; do not create downstream implementation until its decision is explicit.

## Resume interrupted work

For W-002, read its row, [work/W-002.md](W-002.md), parent W-001, and E7 only. Inspect checkpoint, Git source, decision/evidence refs, and next action. If no pilot decision is recorded, leave implementation unstarted.

## Amend accepted criteria

Append a decision object with all fields: `affected_criteria`, `previous_wording`, `proposed_wording`, `change_type`, `reason`, `supporting_evidence`, `user_impact`, `verification_impact`, `approval_source`, `approval_ref`. Keep `approval_source: "unverified"` and old accepted wording until an unclear or material decision is corroborated.

## Submit completion evidence

For each required criterion record source commit/fingerprint, accepted baseline, configured check ID, actual argv array, exit status, result, applicability, summary/location, provenance, environment, and test counts when configured. A negative experiment can have `result: "pass"` when the method/report criterion passed and its summary says the hypothesis was rejected. Do not relabel a failed behavior check as pass.

When submitting after review, append the new review entry after prior entries. Preserve earlier `changes_required` reports, resolve each finding with evidence, and leave the item outside `done` unless the latest review entry is a fresh `ready` recommendation.
