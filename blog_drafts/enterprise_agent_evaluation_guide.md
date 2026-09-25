# Testing Agents by What They Do: A Practical Evaluation Guide

*For engineers and engineering managers deciding how much evaluation a tool-using agent needs.*

*Unpublished educational draft, not a product specification. See the [project manifest](../manifest.md) for the evolving direction.*

## 1. Start with the consequence

A support assistant can produce a fluent answer and still be wrong. An agent that issues a refund can produce a fluent answer **and change the wrong account**. Both need evaluation, but the second also needs a test that inspects the resulting state.

Modern evaluation tools already support code checks, model judges, full trajectories, and production traces. The engineering question is which evidence a particular agent needs before release. A trace shows what the agent attempted; an independent state check shows what happened.

Our position: **increase evaluation depth with the agent's ability to change the world and the cost of a mistake.** For each property, use the simplest check that can establish it.

Before choosing tools, ask:

1. **What can the agent change?** A draft answer, ticket, payment, and production database have different consequences.
2. **What counts as success?** Write an observable outcome such as “the correct order was refunded once.”
3. **What must never happen?** Examples include changing an unauthorized record or spending beyond a limit.
4. **What can vary between runs?** Model choices, API failures, records, and random events determine which scenarios to repeat.

---

## 2. Separate the agent, the test world, and the grader

The **agent under test** sees a task and calls tools. The **environment** answers those calls and records resulting changes. An **independent grader** inspects the outcome, including facts the agent was not allowed to see. Adversarial tests can feed the agent malicious or misleading inputs through the same environment.

In [AgentBeats](https://docs.agentbeats.dev/tutorial/), the subject is called a *purple agent* and an assessment is packaged as a *green agent*. Those names can help when using that framework; the separation of roles matters more than the colors or protocol. A local test harness can use the same design.

An internal validator may help the agent avoid a malformed tool call. It cannot replace the independent grader. A schema check establishes that the call has the expected shape; it does not establish that the agent chose the right customer or made the right decision.

---

## 3. Build only as much environment as the task needs

A useful environment is a resettable stand-in for the systems the agent acts on. It need not copy an entire enterprise stack.

| Starting point | What it provides | Good first use |
| --- | --- | --- |
| Recorded fixture | Stable tool responses | Read-only retrieval or extraction |
| Small state store | Records that change after actions | Tickets, orders, refunds |
| Seeded scenario generator | Controlled variation and failure injection | Rare cases, budgets, retries |

For a refund agent, a small environment might contain an order table, a refund ledger, an authorization rule, and a tool that sometimes times out *after* committing a write. That last case tests whether a retry duplicates the refund.

Make runs **resettable** and **reproducible**. Record the seed, scenario, tool versions, and agent version. Randomness is fine when its draws can be reconstructed. Keep ground truth outside the agent's view. Check the environment against real incidents or domain expert judgment so a convenient simulation does not become a misleading one.

Our [synthetic claims study](../../README.md) illustrates the risk: the environment's reward ranking differed from the financial loss ranking. The [subsequent statistical report](../../experiments/analysis/statistical_report.md) also found that agents did not all face identical claim streams despite a shared seed. Those results are useful for finding evaluation flaws; they do not establish which policy would perform best on real claims.

---

## 4. Choose the evidence the task needs

| Check | What it can establish | What it cannot establish alone |
| --- | --- | --- |
| Code assertions | Schemas, policy limits, and specified state/outcome invariants | Correctness beyond the encoded rules or without trustworthy ground truth |
| Human or model review | Clarity, relevance, and other qualities requiring judgment | Whether an external record actually changed |
| Trajectory review | Tool order, retries, and budget use | Whether the resulting state is correct without ground truth |
| Resettable environment | Outcomes, side effects, and recovery under controlled conditions | Performance on every real-world distribution |
| Production monitoring | New failures and changing usage after release | Reliable ground truth for every live case |

This is a menu, not a maturity ladder. A read-only assistant may need a strong factuality review and no simulated ledger. A high-impact write action deserves outcome checks and adversarial cases even if its final response is easy to grade.

Use code when the rule really captures the property. A JSON schema proves shape, not intent. Calibrate model judges against human examples, inspect disagreements, and report performance on the cases that matter. There is no universal agreement percentage that makes a judge safe to use.

Tools including [LangSmith](https://www.langchain.com/langsmith/evaluation), [Braintrust](https://www.braintrust.dev/blog/stateful-agent-evals), and [Arize Phoenix](https://arize.com/docs/phoenix/evaluation/llm-evals/evaluator-traces) already support combinations of these checks. The hard part is defining the outcome and maintaining a trustworthy test world for it.

---

## 5. Check steps and outcomes

Run inexpensive checks when a tool call is made: schema validity, authorization scope, idempotency key, and budget remaining. After the episode, inspect the final state and any prohibited side effects. Review the trajectory when the path matters, such as checking authorization before a write.

A model judge can help with subjective decisions or explain a failure cluster. Putting one after every step can add cost and latency without improving the release decision. Use it where human examples show it adds useful signal.

Keep separate metrics for task success, harmful actions, cost, and latency. A single weighted score can hide a severe policy violation behind good prose or low cost.

---

## 6. Match the test to the agent

| Agent | Minimum useful evidence | Add when needed |
| --- | --- | --- |
| Knowledge assistant | Factuality, citation, and privacy cases | Multi-turn checks when it retains context |
| Structured worker | Schema checks and task-level correctness | Execution in a sandbox for generated SQL or code |
| Sequential decision agent | Resettable scenarios, outcome checks, budget accounting | Rare-event stress tests and human review of consequential decisions |
| Agent with write privileges | All relevant checks above plus unauthorized-action tests | Adversarial inputs, rollback and retry scenarios, production outcome monitoring |

These are starting points, not compliance rules. The agent's permissions and failure cost should determine the release bar.

---

## 7. Turn failures into better tests

Start with the cheap fixes. If the agent calls the wrong tool, clarify its tool contract or add a guard. If the agent fails after a timeout, add an idempotency rule and a retry scenario. If a production incident reveals a missing case, remove sensitive data, confirm the expected outcome with a domain owner, and add a regression test.

Recalibrate the simulator as real workloads change. Keep a held-out scenario set so repeated prompt changes do not overfit to public examples. Compare the agent with a simple rules-based baseline and the previous release. Repeat stochastic runs and show the spread, not only the best score.

Evaluation data can support model training later, but a high-scoring trajectory is not automatically a good training example. First verify the reward, outcome, privacy rights, and data quality. In our claims study, reward and financial loss ranked agents differently; training directly on the wrong reward would reinforce the wrong behavior.

---

## 8. Further reading

- [AgentBeats](https://docs.agentbeats.dev/tutorial/) packages assessments as green agents and subjects as purple agents.
- [OpenEnv](https://huggingface.co/docs/openenv/index) provides execution environments for agent interactions.
- [UK AI Safety Institute Inspect](https://inspect.aisi.org.uk/agents.html) supports agent evaluations, limits, and external agent bridges.
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) catalogs agent security risks.

The central claim is modest: as agents acquire memory, budgets, tools, and permission to write, evaluate observable consequences as well as responses. The test world and its grader deserve the same scrutiny as the agent.
