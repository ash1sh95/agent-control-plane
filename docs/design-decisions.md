# Design decisions (ADRs)

## ADR-1: Judge-before-action, outside the agent
**Decision:** all tool calls pass a gate the agent cannot see around.
**Why:** the planner is the least trustworthy component (injectable,
confusable, loop-prone). Safety inside the prompt is advisory; safety in
the execution path is structural.
**Trade-off:** one extra evaluation per call; negligible next to an LLM call.

## ADR-2: Deterministic rules are the default judge; LLMs only add strictness
**Decision:** `RuleBasedJudge` by default; `CompositeJudge` takes the
strictest verdict and an LLM judge can never override a rule DENY, and
fails closed (require-approval) when unavailable.
**Why:** a control plane whose decisions cannot be reproduced in a unit
test cannot be evaluated, audited, or defended in review.
**Trade-off:** rules miss novel attacks a model might catch -- accepted,
and mitigated by the eval-first workflow for new attack classes.

## ADR-3: JSONL audit log + JSON approval queue as the storage contract
**Decision:** boring files first; Postgres/Delta/Redis slot behind the
same two classes.
**Why:** the *contract* (every decision attributable; approvals are
per-call state flips) is the product. Storage is replaceable; semantics
are not. JSONL is greppable, diffable, and has zero setup cost.
**Trade-off:** single-host by default; documented, not hidden (LIMITS).

## ADR-4: Local-first model routing with metered frontier fallback
**Decision:** Ollama/local by default, frontier only for hard tasks or
local failure, every call metered by the router.
**Why:** agent loops multiply token volume (context re-sent per step);
local marginal cost is ~zero and 2025 MoE models (gpt-oss-20b,
Qwen3-Coder-30B) made the local tier genuinely capable. Metering makes
the split a measurable decision, not a vibe.
**Trade-off:** local quality ceiling -- hence the explicit `hard=True`
escalation path instead of pretending local is always enough.

## ADR-5: MCP supported at the boundary; native function calling first-class
**Decision:** tools are native functions/specs in-repo; `mcp_adapter.py`
translates MCP-style discovery/calls into the same governed `ToolCall`.
**Why:** MCP standardises discovery/transport, not trust or selection
quality. For a small curated tool set native calling is simpler and
lower-latency; for shared multi-agent ecosystems MCP earns its place.
Governance must be transport-independent either way.
**Trade-off:** no full MCP transport (stdio/SSE) implementation -- a
labelled stub boundary, not a silent gap.

## ADR-6: Eval the decisions, not the answers
**Decision:** the harness scores gate verdicts (pass / false allow /
false deny) and CI fails on any false allow; attacks land as failing
eval cases before policies.
**Why:** for a control plane the verdict *is* the product, and
false-allow is an asymmetric, safety-critical metric that a generic
answer-quality score would dilute.
**Trade-off:** a small (17-case) set by design; it is a regression floor,
not a red-team substitute -- stated in LIMITS.
