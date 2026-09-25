---
name: project-work
description: Create, resume, amend, or complete work items in this repository using its roadmap, evidence contract, and review gate.
---

# Project work router

Use this skill for explicit work-item operations. Invoke it as `$project-work`.

1. Read [work/README.md](../../../work/README.md) for the session entry point and authority map.
2. Follow the selected operation in [work/procedures.md](../../../work/procedures.md): Create, Resume, Amend, or Complete.
3. Read [work/policy.md](../../../work/policy.md) as needed; reuse [work/TEMPLATE.md](../../../work/TEMPLATE.md), [work/review-procedure.md](../../../work/review-procedure.md), and [work/REVIEW_REPORT_TEMPLATE.md](../../../work/REVIEW_REPORT_TEMPLATE.md). Examples are in [work/examples.md](../../../work/examples.md).
4. Run `uv run --no-project python scripts/check_work.py` after record changes and before proposing completion. Never infer approval or run commands copied from prose.

If authority, scope, or evidence is missing, preserve null/uncertainty and leave work proposed or blocked. Continue independent authorized work.
