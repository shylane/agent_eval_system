---
{
  "schema_version": 1,
  "id": "W-000",
  "kind": "task",
  "authorization_ref": null,
  "accepted_criteria_commit": null,
  "implementation_base_commit": null,
  "completion_disposition": "required",
  "ledger_refs": [],
  "criteria": [
    {"id": "W-000-AC1", "required": true, "behavior": "Concrete observable result", "verification_method": "Named review or configured check"}
  ],
  "evidence": [],
  "decisions": [],
  "resolutions": [],
  "reviews": [],
  "blocker": null,
  "disposition": null
}
---

# Work item title

## Outcome
One sentence describing the result.

## Scope
Included: ...

Excluded: ...

## Acceptance criteria
The structured criteria above are authoritative. Keep IDs stable; record accepted wording changes before applying them.

## Execution checkpoint
Current concrete checkpoint, completed work, and next action. Do not copy roadmap status, owner, or priority here.

## Decisions and changes
The structured `decisions` array is authoritative.

## Evidence
The structured `evidence` array is authoritative. Link reports/artifacts via `location`; do not imply a command ran without runner evidence.

## Review
The structured `reviews` and `resolutions` arrays are authoritative. Use [REVIEW_REPORT_TEMPLATE.md](REVIEW_REPORT_TEMPLATE.md).
