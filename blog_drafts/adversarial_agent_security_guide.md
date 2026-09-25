# Testing What an Attacker Can Make an Agent Do

*For AppSec and product teams assessing agents that read untrusted content or call tools.*

*Unpublished educational draft, not a product specification. See the [project manifest](../manifest.md) for the evolving direction.*

This is the security companion to [the evaluation guide](enterprise_agent_evaluation_guide.md). Its focus is the action an attacker can induce, the entry point they control, and the evidence needed to call a test successful.

---

## 1. Threats follow permissions

A prompt injection is dangerous when untrusted text can influence a consequential action. A document, email, search result, or tool response may contain instructions that the agent should treat as data. The impact depends on what the agent can access and change: revealing a private record, issuing a refund, changing a permission, or running code.

The [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) describes risks including goal hijack, tool misuse, and memory poisoning. These are useful categories for threat modeling, but a category alone is not a test. For each agent, identify the trust boundary and the protected action.

Research on [Morris II](https://arxiv.org/abs/2403.02817) showed self-replicating prompt injections in an experimental ecosystem of email assistants. It demonstrates a possible propagation mechanism; it does not establish that every connected enterprise agent can be infected in the same way.

---

## 2. Specify the attacker's control

A useful adversarial case states four things:

1. **Entry point:** chat message, retrieved document, tool response, repository file, or another surface the agent reads.
2. **Knowledge:** what the attacker knows about tools, policies, and prompts.
3. **Control:** which bytes or records they can actually change.
4. **Objective:** the prohibited result they want, such as an unauthorized write or a private-data disclosure.

Vary knowledge deliberately. A chat-only test probes the public surface. A contract-aware test assumes the attacker knows tool names and schemas. An insider-style test may assume access to prompts or implementation details. These are test conditions, not claims that every attacker has that access.

Keep the attacker objective separate from the normal task objective. The same harness can run both tests, but the reports should distinguish task success from exploit success. A model judge may help triage attempts; the final security verdict should inspect the tool call, changed state, or data disclosed whenever those can be observed.

---

## 3. Test four failure modes

Organize tests by the failure they seek to cause. Record the attacker's entry point and control separately, since the same failure may be reached in several ways.

| Failure mode | Example objective | Observable proof |
| --- | --- | --- |
| Business rule abuse | Obtain a refund outside policy | Refund ledger and policy state |
| Instruction injection | Turn text in a document into a tool command | Tool-call trace and resulting state |
| Privacy or authorization failure | Reveal a record the requester cannot access | Returned data and access decision |
| Tool or infrastructure misuse | Call a privileged endpoint with unsafe arguments | Server-side authorization and execution logs |

A test can cross categories. A malicious invoice might use an injection to cause a privacy failure. Record the entry point and objective separately so teams can identify whether the fix belongs in the prompt, the tool authorization layer, or the underlying service.

Do not treat a detector's “blocked” label as proof of safety. Confirm that the prohibited effect did not occur. Also measure false positives: a system that blocks legitimate requests may be secure on paper and unusable in practice.

---

## 4. Put tests where they can change a release decision

Run a small set of known attack regressions in the developer loop. Before a consequential release, test the agent against untrusted content, changing state, tool errors, and authorization boundaries in a resettable environment. Run more expensive adaptive attacks where the agent's permissions and exposed surfaces justify them. In production, watch for suspicious tool use and investigate incidents; online monitoring is not a substitute for pre-release testing.

Each security scenario should record the agent version, attack surface, attacker control, expected boundary, actual tool actions, final state, and whether the legitimate task still worked. Share a discovered payload across agents **only when the receiving agent has the same relevant surface**. A passing test shows resistance to that case and configuration, not general immunity.

Use service-side authorization, least privilege, idempotency, and network boundaries as primary controls. A model-level defense can help, but it should not be the only barrier between an injected instruction and a consequential action.

---

## 5. Sources

- [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/): a risk taxonomy, not a certification.
- [NIST AI 600-1](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence): the 2024 Generative AI Profile.
- [Morris II](https://arxiv.org/abs/2403.02817): experimental propagation through connected GenAI email assistants.
- [InjecAgent](https://arxiv.org/abs/2403.02691) and [AgentHarm](https://arxiv.org/abs/2410.09024): research benchmarks for different agent failure modes.
- [PAIR](https://arxiv.org/abs/2310.08419) and [TAP](https://arxiv.org/abs/2312.02119): automated attack search methods; neither is a complete enterprise threat model.
