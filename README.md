# Agent Systems Evaluation Lab

**Status:** planned; this folder is a new project area, not an implemented platform. The folder name remains `agent_test_lab` to keep links stable while the working title evolves.

The north star is a continuing evaluation partner for agent builders: find where systems break, test why through controlled changes, and measure which improvements hold up. The proposed product has **not** been built. Green/purple terminology comes from [AgentBeats](https://docs.agentbeats.dev/tutorial/); red is our added attacker role. A *world* responds to agent actions, a *scenario* sets up a test, and an independent *verifier* checks the outcome. Versioned artifacts should make valid reuse cheap without recycling stale verdicts. A versioned product-intent contract should help triage world drift, unsupported requests, and possible feature opportunities without letting the system silently redefine scope. See [terms and source notes](references.md) before using other borrowed names.

## Start here in a new thread

Read this page first, then the [manifest](manifest.md) for vision versus current commitments. Use the [experiment ledger](experiments.md) to select work and find dated results; consult [references.md](references.md) for term definitions, primary-source credit, and capability boundaries. The three pieces in [blog_drafts](blog_drafts/) are unpublished educational writing, not product specifications or demonstrated capabilities. Do not rely on past chat messages as the only record of a decision.

## First milestone

Current next step: choose the first synthetic write-capable workflow and establish a narrow incumbent/small-harness baseline ([E7](experiments.md)). Then build a resettable world and show a reproducible multi-turn failure with an independent state check. Record setup/run cost, basic artifact dependencies ([E17](experiments.md)), and what the world does *not* model. A controlled memory or orchestration comparison is the next proof. **Usefulness** means the evidence helps an engineer; **differentiation** requires a fair comparison with existing tools. Publish one focused article after a small measured result, not after a complete platform.

Before implementation, write a short `pilot_brief.md`: chosen synthetic workflow and why; intended users and permitted/forbidden outcomes; concrete state and side effects; one ordered multi-turn failure to reproduce; reference behavior and independent check; baseline tool or harness; budget; and known gaps. Link the eventual dated result from the experiment ledger. The workflow choice is still open. The first pilot succeeds if another engineer can reproduce a consequential result and understand its limits and cost; it does **not** need the later app dossier, autonomous world building, or a startup thesis.

Existing healthcare claims work elsewhere in this repository is background and may offer evaluation lessons; it is not this project's implementation. Keep new code, tests, results, and decisions under this folder unless shared infrastructure genuinely belongs at the repository level.

## Project work

Use [roadmap.md](roadmap.md) to select work and the [work-record contract](work/README.md) to create or resume it. Detailed scope and evidence live in linked `work/` records. A proposed item does not authorize implementation.
