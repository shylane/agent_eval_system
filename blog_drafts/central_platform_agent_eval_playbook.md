# A Shared Release Gate for Agents That Change State

*An operating model for AI Platform, product engineering, and AppSec teams.*

*Unpublished educational draft, not a product specification. See the [project manifest](../manifest.md) for the evolving direction.*

The [evaluation guide](enterprise_agent_evaluation_guide.md) explains what to measure; the [security guide](adversarial_agent_security_guide.md) explains what to attack. This playbook asks what a central team should actually own so individual product teams can test their agents without adopting one agent framework.

---

## 1. Standardize evidence, not agent implementations

A central platform has a real problem: several teams may build agents with different tools, while leadership needs to know which versions were tested and what they were allowed to do. A mandate to rebuild every agent on one framework can slow adoption. A dashboard alone cannot establish that a consequential action was correct.

The smallest useful shared service is a **release record**: a versioned description of the agent, scenarios, expected outcomes, observed state changes, failures, and approval decisions. Teams can keep their existing runtimes if they expose enough behavior to run those tests.

Our proposal is to start with agents that write to external systems. Their success can often be checked against state changes, and their failures are expensive enough to justify a release gate. Read-only agents can use lighter checks.

---

## 2. Make ownership explicit

| Work | Product team | AI Platform | AppSec or risk owner |
| --- | --- | --- | --- |
| Task, business rules, and acceptable outcomes | Owns | Advises | Reviews high-risk boundaries |
| Domain fixtures and state checks | Owns content | Provides runner, storage, and review workflow | Adds abuse cases |
| Agent adapter and tool permissions | Implements | Defines minimum contract and isolation | Reviews privileges |
| Attack scenarios and prohibited outcomes | Supports | Runs and records tests | Owns threat model and acceptance decision |
| Release decision | Owns functional sign-off | Supplies evidence | Signs off where policy requires it |

This division prevents a central team from inventing domain ground truth it cannot validate. It also prevents product teams from scoring their own agent with the same unchecked assumptions used to build it.

---

## 3. Ask for a small, testable contract

For a first release, an agent needs an adapter that can accept a task, call test tools, and return an outcome. The test runner also needs an agent version, tool permissions, resource limits, and a way to reset the scenario. Capture tool calls and final state with stable identifiers.

A2A can be useful when agents already expose an A2A interface. MCP can be useful for tool access. Neither is required to test a Python service or a custom workflow. [A2A originated at Google](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) and [MCP at Anthropic](https://www.anthropic.com/news/model-context-protocol); [AgentBeats](https://docs.agentbeats.dev/tutorial/) uses them together for portable assessments. A manifest and tool schema alone will not make every agent evaluable: state setup, permissions, and domain scoring still require work.

---

## 4. Build the shared core first

The initial platform service should do five things well:

1. **Run a versioned scenario** against an agent adapter in an isolated, resettable environment.
2. **Record evidence:** scenario and seed, agent and tool versions, actions, final state, costs, and failures.
3. **Apply independent checks** supplied by the domain owner and security team.
4. **Compare releases** against a simple baseline and the previous agent version.
5. **Export a reviewable report** with failed cases and known gaps.

Use existing observability and evaluation products where they already solve the problem. [LangSmith](https://www.langchain.com/langsmith/evaluation) and [Braintrust](https://www.braintrust.dev/blog/stateful-agent-evals) support multi-step evaluation and CI workflows; [Inspect](https://inspect.aisi.org.uk/agents.html) and [OpenEnv](https://huggingface.co/docs/openenv/index) provide useful evaluation and environment components. The opportunity for a central team is its own domain scenarios, permission boundaries, outcome checks, and release decisions.

Add a shared dataset registry, adaptive red-team service, or model-training export only when teams demonstrate a repeated need. Each brings maintenance and governance work. Training on “top” trajectories is particularly risky until the reward and labels have been validated.

---

## 5. Keep the scorer independent

An agent may validate its own tool arguments or ask a model to reconsider a step. Those checks help execution. The release scorer should inspect ground truth held by the environment or an external reviewer.

For example, “amount is positive” is an argument check. “The authorized customer received exactly one refund for the correct amount” is an outcome check. Both are useful, but they answer different questions. Store the checks and their versions with each run so a score can be reproduced later.

A signed record can show what tests were run and whether the record changed afterward. It does not, by itself, establish compliance with SOC 2, HIPAA, or any law. The relevant control owner must decide what evidence and review are required.

---

## 6. Make the release decision easy to inspect

A product team submits an agent version and a small scenario set during development. The shared runner returns concrete failures: “refund was issued twice after a timeout,” “authorization was checked after the write,” or “the agent exceeded its tool budget.” Before release, the team runs the broader scenario set and security cases. The report shows per-case outcomes and differences from the prior version.

The gate should block on explicit high-severity failures, such as an unauthorized write. For graded quality metrics, thresholds should be chosen from observed baselines and reviewed with the domain owner. A universal score such as 0.90 can conceal severe failures and encourages teams to optimize the metric rather than the task.

The first pilot should use one workflow and one consequential action. Measure scenario authoring time, run cost, reproducibility, defects found before release, and whether the domain owner trusts the verdict. Those numbers determine whether a shared service is worth expanding.

---

## 7. Expand only when the pilot earns it

A platform team should expand the service when multiple product teams can reuse the runner, report, and common failure scenarios without extensive custom integration. If every new agent requires a new simulator and bespoke approval process, the immediate need may be domain consulting rather than a horizontal platform.

A useful second pilot should have different business rules but similar release mechanics. Compare how much of the first pilot's code and evidence format carries over. That reuse, along with defects detected and time saved, is the case for central investment.

---

## 8. Further reading

- [AgentBeats](https://docs.agentbeats.dev/tutorial/) for portable green and purple agent assessments.
- [OpenEnv](https://huggingface.co/docs/openenv/index) for agent execution environments.
- [UK AI Safety Institute Inspect](https://inspect.aisi.org.uk/agents.html) for evaluation runners and agent bridges.
- [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) for security risk categories.

This is an operating proposal, not a claim that a complete enterprise evaluation product exists in this repository. The first proof should be a narrow release gate whose verdict a domain owner can inspect and challenge.
