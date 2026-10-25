# Architecture

## The one-sentence version
No tool call executes in the agent until a small, deterministic, audited
control plane has said *yes* — and for risky calls, until a human has.

## Components

| Component | File | Responsibility |
|---|---|---|
| Gate | `gate.py` | Single choke point; runs checks in defense-in-depth order |
| Models | `models.py` | `ToolCall`, `Decision`, stable args hashing |
| Policies | `policies.py` | Pure functions: call -> PolicyResult or None |
| Judges | `judge.py` | RuleBasedJudge (default), LLMJudge (Ollama/frontier), CompositeJudge |
| Rate limiter | `rate_limiter.py` | Sliding-window, per-tool per-session budgets |
| Dedupe | `dedupe.py` | Same tool+args per case/session executed at most once |
| Approvals | `approvals.py` | File-backed human approval queue (front-end agnostic) |
| Audit | `audit.py` | Append-only JSONL of *every* decision, allows included |
| Router | `router.py` | Local-first model routing, frontier fallback, token/cost metering |
| Agent | `agent.py` | Demo planner + bounded executor; LangGraph graph when installed |
| MCP adapter | `mcp_adapter.py` | Translates MCP-style tool specs/calls into governed `ToolCall`s; native calling stays first-class |
| Evals | `eval_runner.py`, `evals/dataset.jsonl` | Verdict-level regression suite for the gate itself |

## Gate evaluation order (and why)
1. **Known tools** — cheapest check; unknown tools are the classic confused-agent failure.
2. **Duplicate** — before rate limits, so the reason reported is the *actionable* one.
3. **Rate limit** — before the judge, so a flooding agent cannot burn judge/LLM cost either.
4. **Judge** — policy verdicts aggregated by strictness (deny > approval > allow),
   so rule authors never rely on ordering for safety.
5. **Approval queue** — `require_approval` is a *state*, not a slower allow:
   the call does not execute, a request is persisted, and execution can only
   happen after an out-of-band human decision.

Only allowed calls consume rate-limit budget and dedupe slots. A denied call
must not poison a later legitimate retry — a subtle bug in naive designs.

## Trust boundaries
- The **agent/planner is untrusted**: it may be prompt-injected, confused, or
  stuck in a loop. All safety lives outside it.
- The **judge is semi-trusted**: an LLM judge can be wrong or unavailable,
  so it fails closed (require-approval) and can never override a rule DENY
  (`CompositeJudge`).
- **Tools are untrusted in the other direction**: their *arguments* are
  treated as attacker-controlled input (injection patterns, traversal,
  secret payloads are scanned in arguments, not just prompts).

## State & storage
Deliberately boring: JSONL audit log + a JSON approval queue on local disk.
Both are the *contracts*, not the product — swap in Postgres/Redis/a queue
service behind the same two classes for multi-host deployments. This mirrors
enterprise practice: decisions and approvals land in a governed table
(e.g. a Delta table behind Unity Catalog), inference stays stateless.

## Failure modes designed for
- Judge backend down -> require-approval, never allow.
- Frontier key missing -> labelled stub response, accounting still recorded.
- Agent loops forever -> `max_steps` + dedupe + rate limits, three independent caps.
- Tool throws -> bounded retries (`max_retries`), error recorded in the step trace.
