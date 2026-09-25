# Agent Systems Evaluation Lab - Project Manifest

**Status:** intended vision and proposed first build; no new capability demonstrated yet. **Updated:** 2026-09-25. **Owner:** project maintainer.

## North star

Build a continuing evaluation partner for teams developing agent systems. It should find **where a system breaks**, test **why** through controlled changes, and measure **what actually improves it**. Its output is not just a score or failure list, but a map of tested operating limits and the evidence behind them. It may also surface evidence-backed product opportunities; it does not decide the product roadmap.

The intended system combines safe production observation with deep pre-production experiments in application-specific, resettable worlds. It should adapt to different proprietary workflows rather than assume one public benchmark or canned environment fits them all. This is a direction to validate, not a claim that autonomous world generation or architecture diagnosis already works.

The first audience is an internal AI/platform team; OSS and a commercial product are possible paths after a useful proof and a measured advantage over existing tools.

## Four evaluation modes

1. **Production signals:** observe traces, outcomes, side effects, drift, and incidents without perturbing live customer state. Use them to propose new tests, world checks, and product hypotheses, not to infer unseen counterfactuals or user intent from traces alone.
2. **Continuous offline evaluation:** safely run production-derived and newly generated cases against a validated, versioned world as the agent changes. Freeze the world and checks within each comparison batch; promote revisions between batches and label which results remain comparable. World and scenario versions may evolve independently.
3. **Pre-production discovery:** adapt scenarios, worlds, and bounded adversarial inputs to find failures and test architectural choices such as memory, orchestration, and improvement loops.
4. **Release measurement:** use a pinned, held-out suite and stated world version for comparable candidate decisions. Refresh it deliberately, never silently.

Version the agent, world, scenario set, verifier, policy, and relevant execution configuration separately. Validated production-derived trajectories may later become training candidates, subject to rights and evaluation isolation.

Before connecting a real application, define an approved capture scope, read-only access where applicable, redaction and retention rules, and a policy for collection overhead or failure. Offline experiments must not reuse production write credentials.

## The loop

`Observe -> triage divergence -> propose world and checks -> validate world -> generate reachable scenarios -> challenge candidate -> verify effects -> compare -> promote trusted tests`

The green/purple assessment terms below come from [AgentBeats](https://docs.agentbeats.dev/tutorial/). We add red as a bounded attacker role; the mapping is a working project convention.

- **Green (assessment):** orchestrates world construction, scenarios, checks, coverage, and evidence. These are logical roles, not necessarily separate LLM processes.
- **World builder:** creates application-specific tool behavior, mutable state, identities, time, reset logic, and declared limits of fidelity from code, contracts, policies, traces, and domain input. It tests new branches against reference behavior and repairs gaps rather than assuming a plausible simulation is correct.
- **Scenario generator:** chooses starting state, task, events, and coverage targets. The world may help sample valid scenarios, but *generating a case* and *responding correctly to the agent's actions* are distinct jobs.
- **Red (attacker):** controls only specified hostile inputs or events. It cannot change hidden truth, the world contract, or scoring rules.
- **Purple (candidate):** runs the real agent workflow against the isolated world; it may not alter the verifier or hidden test state.
- **Independent evaluator:** checks final state and safety invariants, then reports agent failure, invalid scenario, world gap, verifier defect, or infrastructure error separately.
- **Control plane:** tracks provenance, trace completeness, coverage, cost, approvals, versions, and release evidence. It routes a divergence to world repair, a candidate test, a product-opportunity review, or quarantine; it cannot quietly rewrite the product's scope or a release verdict.

Adaptive multi-turn red teaming such as [Promptfoo Hydra](https://www.promptfoo.dev/docs/red-team/strategies/hydra/) is prior art; our three-role design is not an AgentBeats feature claim. Separation of authority matters more than deploying three agents; the independent verifier must remain protected from both candidate and attacker. See the [terms and attribution notes](references.md).

## Evidence product

For a consequential finding, produce a reproducible **limits record**: task and scenario provenance; agent/world/verifier versions; tested conditions and coverage; before/after effects; independent outcome check; baseline or intervention comparison; uncertainty and alternative explanations; cost; and known untested territory. This supports an engineering decision, not a claim of universal safety.

Over time, retain reusable world fragments, fixtures, scenarios, checks, minimized failures, and validated claims with their sources, assumptions, dependencies, owners, and revision history. This is an **evidence memory**, not a store of timeless truths: changing a dependency can invalidate a cached result or a previously checked claim.

A later research direction is an **app dossier**: a working model of the application's purpose, users, workflow, observed behavior, and unknowns that helps the lab choose probes and interpret results. It could start from maker-supplied descriptions, design and vision documents, code, policies, examples, and traces, then ask makers targeted questions to check important ambiguities. Keep owner-approved intent, observed evidence, and the lab's own hypotheses separate. Every consequential note needs provenance, scope, version, and a status such as untested, corroborated, refuted, or stale. The dossier may suggest tests and questions; it cannot turn an inference into product policy or certify its own accuracy. Test whether it improves decisions enough to justify its upkeep before building it broadly; see [E24-E25](experiments.md).

## Scope and drift discipline

Each application needs a versioned **product-intent contract** supplied by its owner: intended users and jobs, supported actions, known exclusions, allowed side effects, success measures, safety obligations, and test budgets. The lab can suggest revisions, but cannot infer or approve the contract from traces alone.

When new production evidence conflicts with the test world, distinguish an instrumentation gap, a changed application or policy, a shifted usage pattern, a world-fidelity gap, a candidate defect, an unsupported but potentially valuable request, misuse, and unresolved cases. A world repair can itself create drift: check it against code, contracts, staging, or a domain owner, and rerun fixed reference cases before promotion. Keep historical cases so adapting to recent traffic does not erase rare regressions.

Out-of-scope cases remain visible with a reason and owner; they do not vanish from failure counts retroactively. An unsupported request can be a feature opportunity while the expected agent behavior today is to decline it safely. Reachable security and authorization risks still require assessment even when the requested feature is outside the charter. New feature candidates are ranked for human review by evidence of user value, product fit, risk, and estimated effort, not trace frequency alone; production traces omit non-users and can be manipulated. Discovery runs under budgets and stopping rules; unresolved cases are queued, not looped indefinitely.

Turning traces into offline cases is already supported by [Veris](https://docs.veris.ai/use-cases/continuous-improvement) and production backtesting is described by [LangSmith](https://docs.langchain.com/langsmith/evaluation-types). The unproven bet here is reliable **divergence classification and bounded routing**, not trace ingestion itself.

## Design rules

1. **Code-first verification.** Use executable checks for state changes, permissions, budgets, ordering, and other observable facts. LLMs may draft code and handle genuinely semantic judgments; generated checks must pass known positive, negative, and boundary examples before use.
2. **Evidence has levels.** A recorded-path replay is grounded but narrow. A new branch in a generated world is a hypothesis until checked against code, contracts, staging, domain rules, or a trusted reference. Unsupported behavior is not an agent failure. Capture trace gaps and side effects where authorized; a trace alone is not the outcome.
3. **Test sequences, not just prompts.** Model legal actions and preconditions. Use constrained combinations and ordered-event coverage for multi-turn effects; spend deeper search on high-risk writes, retries, authorization, and cross-service behavior.
4. **Control cost through selective reuse.** Reject impossible and duplicate cases before agent execution; cap turns and spend; minimize verified failures. Reuse unchanged test ingredients and deterministic work, but rerun a changed candidate and sample stochastic behavior afresh. Track confirmed new failures per unit of cost, cache savings, and stale-cache errors, not raw test count or cache-hit rate alone.
5. **Keep the four modes distinct.** Production observation, continuous offline evaluation, adaptive pre-production discovery, and pinned release measurement serve different decisions. Report coverage and version changes alongside scores; do not treat a changing world or discovery suite as a fixed benchmark.
6. **Autonomy needs anchors.** Automate proposal, execution, triage, and world repair, prioritizing uncertain or risky parts of the world. Novel high-impact rules, scope changes, and release-gating verifiers need independent validation; agents must not certify only one another.
7. **Architecture claims require interventions.** A trace or code review can suggest a cause, not establish it. Compare designs on the same tasks, world, model, and budget; vary one architectural factor where possible. Report the conditions tested and alternative explanations, not a universal verdict.
8. **Cover systems, not only prompts.** Probe memory across long histories, revised facts, interference, retrieval, forgetting, and access changes; orchestration across dependencies, fan-out, handoffs, retries, and worker failure; improvement loops across repeated changes and held-out regressions; and security across bounded attacker control and independently observed prohibited outcomes. Choose probes by relevance and risk, not by a universal checklist.

## First wedge and build order

The initial experiment will use one synthetic, write-capable workflow with observable side effects. A refund/order flow is a *candidate*, not a committed domain. It should include a failure requiring **multiple turns and event order**, such as a timeout after a committed write followed by a retry. The existing claims environment in this repo offers reward-calibration lessons, but does not prove transfer to enterprise apps.

1. Define the workflow, a minimal product-intent and outcome contract, and a narrow baseline using an existing tool or a small hand-written harness. Record what an incumbent can already do before building broadly.
2. Capture tool I/O, versions, and scoped before/after effects; replay a known path cheaply. Give each world, scenario, verifier, and run a simple versioned identity and dependency record from the start; a graph database is not required for the first proof.
3. Build a resettable reference world and independent code-based outcome checks. Label behavior beyond reference evidence as unvalidated.
4. Generate legal, multi-turn scenario sequences in code; add limited LLM wording and red-team tactics. Repair or reject cases when they exceed world fidelity.
5. Produce one limits record with a baseline, cost, and reproducible finding; then probe one memory or orchestration choice through a controlled comparison.
6. Repeat on a materially different workflow to test transfer, and compare build, buy, or compose before claiming a general platform.

Evaluating a candidate agent's self-improvement loop is distinct from autonomously improving this evaluation lab. Both are later hypotheses. Any proposed change must improve held-out outcomes without unacceptable regressions or excess cost.

[Chronicle](https://github.com/theagentplane/chronicle) provides boundary record/replay; its recorded input/output does not establish internal side effects. [OpenEnv](https://github.com/huggingface/OpenEnv) provides agent-environment interfaces, and [Inspect](https://inspect.aisi.org.uk/) provides evaluation infrastructure. These are possible components or baselines, not evidence that they generate validated, application-specific worlds. [Veris](https://docs.veris.ai/use-cases/continuous-improvement) already documents simulation, trace-derived scenarios, grading, and fix suggestions; benchmark it before rebuilding broad capabilities. The [source notes](references.md) spell out what we credit and what remains our hypothesis.

## Success and boundaries

Judge the work by **time to a validated world**, coverage of relevant state transitions, agreement with a reference system, verified consequential failures or architecture tradeoffs per dollar and reviewer-hour, false-positive rate, decision usefulness, and repeatability across unlike workflows. For later drift triage, measure correct routing, time to detect a stale world, false exclusions, and cost. A useful first proof and a differentiated product are separate thresholds.

Not in the initial scope: perturbing live production, claiming a universal world generator or bullet-proof architecture assessment, treating a changing discovery-suite score as a release metric, or training an agent by RL. A later research path is generating varied, validated environments and scenarios as training curricula, not just exporting traces. [RLAnything](https://arxiv.org/abs/2602.02488) is inspiration for adaptive environment variation, but our proposed evaluation-first use is distinct and unproven. Test whether it produces learning gains without evaluation leakage, cost blowups, or rights violations.

Formal checks may later establish *narrow* invariants under stated assumptions and model bounds; they cannot prove arbitrary LLM behavior or that a generated world matches production. Where an invariant can be enforced in application code or policy, enforce it there too. Cross-project reuse must respect tenant boundaries and revalidate business meaning, not just matching tool names. See the [reuse experiments](experiments.md) and [source notes](references.md).

## Demonstrated so far

None of the proposed lab capabilities have been demonstrated in this folder. The existing healthcare claims work elsewhere in the repository supplies evaluation lessons, not proof of this system's generality.

## Publication rule

Keep the three articles as unpublished educational drafts. First produce a small, reproducible win: a concrete stateful failure or architecture tradeoff, an independent check, a baseline, setup/run cost, and stated limits. Then publish **one** focused article around that evidence. The practical evaluation guide is the default first piece; lead with the security or platform draft instead only if the proof directly supports it. Revise the other drafts only if they serve a distinct audience. A useful OSS artifact can be part of the proof, but publication does not require a startup claim. Public examples must use synthetic or cleared data and respect employer IP and disclosure rules.

## How this document changes

This file labels three things separately: **intended vision** (what we want to test), **current commitments** (what we will build next), and **demonstrated evidence** (what has worked). The ledger holds alternatives, hypotheses, results, and rejected paths. Promote a capability claim only after recording evidence in [experiments.md](experiments.md). Define borrowed terms and track primary sources in [references.md](references.md). Keep [the evaluation guide](blog_drafts/enterprise_agent_evaluation_guide.md), [security guide](blog_drafts/adversarial_agent_security_guide.md), and [platform playbook](blog_drafts/central_platform_agent_eval_playbook.md) educational rather than treating them as product specifications.
