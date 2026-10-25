# Research notes — what this design is grounded in (2025-26 practice)

Written Oct 2026. Each design choice in this repo traces to a source below,
a named risk, or an eval case. This is the "why", kept separate from the
"how" in ARCHITECTURE.md.

## 1. Agent runtime patterns — LangGraph, with an escape hatch
LangGraph's graph model (nodes, state, checkpoints, human-in-the-loop
interrupts) is the current default shape for production agents, and MLflow's
own agent cookbook builds on it. This repo uses LangGraph *when installed*
(`agent.build_langgraph_agent`) and an identical plain loop otherwise --
because the control plane, not the orchestrator, is the durable layer.
Frameworks churn; the gate contract (propose -> judge -> execute) does not.
- MLflow LangGraph agent cookbook: https://mlflow.org/cookbook/langgraph-agent/

## 2. MCP vs native function calling — governance, not religion
The 2025-26 debate, steelmanned both ways:
- **Native function calling**: fewer hops, lower latency, no extra
  discovery/transport surface to govern; the model selects from a curated
  set you control. Right default for a small, sensitive, fixed tool set.
- **MCP (Model Context Protocol)**: standardises tool *discovery and
  transport* across hosts/agents; Databricks itself now exposes UC
  functions, Genie and Vector Search as governed MCP servers, and runs an
  MCP catalog. Right choice when tools must be shared across many agents.
- MCP standardises transport; it does **not** improve a model's tool
  *selection*, and a discovered tool is not a trusted tool.
**This repo's stance:** native first-class (`tools.py`, function specs),
MCP supported at the boundary (`mcp_adapter.py`) with the rule that
MCP-originated calls are translated to `ToolCall` and pass the same gate.
Whichever transport wins, the governance layer is unchanged.

## 3. Local models worth gating — gpt-oss & Qwen3-Coder class
MoE releases in 2025 changed local-first economics: total parameters
(memory) decoupled from active parameters (speed).
- **gpt-oss-20b** (OpenAI, Apache-2.0, Aug 2025): 20.9B total / 3.6B active,
  MXFP4, ~14GB on Ollama, designed for 16GB machines, strong tool use.
- **gpt-oss-120b**: ~65GB, single 80GB-class GPU / large unified memory.
- **Qwen3-Coder-30B-A3B** (Jul 2025): 30.5B / 3.3B active, ~19GB, 256K
  native context -- the 32GB+ tier's agentic coder.
The router's defaults and `.env.example` target this class of model via
Ollama (`ACP_LOCAL_MODEL`, `ACP_JUDGE_MODEL`): a small local model is a
credible *judge* precisely because judging is a narrow classification task.
- Local coding-model survey with sizes/scores: https://localaimaster.com/models/best-local-ai-coding-models

## 4. DSPy — prompts are programs, optimise them like it
DSPy treats prompts/signatures as compilable, optimisable artifacts rather
than hand-tuned strings, and MLflow 3 integrates DSPy tracing/optimisation.
Where it fits here: the LLM judge's system prompt and the demo planner are
exactly the kind of narrow, measurable components DSPy optimises against
the eval set. This repo keeps the judge prompt a single named constant
(`LLMJudge.SYSTEM`) so it can be swapped for a DSPy-optimised signature
without touching the gate.
- Background via Databricks DAIS 2025 notes (MLflow 3 + DSPy integrations): https://www.rearc.io/blog/dais-2025-genai-releases

## 5. MLflow 3 — tracing & evaluation for agents
MLflow 3.0 (Jun 2025) made GenAI first-class: OpenTelemetry-based tracing
across 20+ frameworks, LLM judges / scorers (including tool-call
correctness), prompt registry, and the same scorers running in dev and
production. This repo's decision-level eval harness is the deliberately
minimal, dependency-free version of that idea -- and the Databricks
notebook (`databricks/`) logs its results *into* MLflow and Delta, so the
two compose instead of competing.
- MLflow 3 overview: https://docs.azure.cn/en-us/databricks/mlflow3/genai/
- Self-improving agent evaluation loop (scorers incl. tool-call checks): http://mlflow.org/blog/self-improving-agent-loop

## 6. Databricks Mosaic AI — the enterprise shape of this repo
Databricks' production agent stack maps 1:1 onto this project's parts:
**Agent Framework** for build/deploy, **Unity Catalog functions** as
governed tools, **AI Gateway** for model access (rate limiting, payload
logging, guardrails, usage tracking), **MLflow** for tracing/evaluation,
**Vector Search** for governed retrieval. March 2025 added end-to-end
governance across models, tools and data, including MCP support.
`docs/databricks-mapping.md` is the full translation table; the point of
building it locally first is that the patterns are learnable and testable
without a workspace.
- Databricks on Databricks (Agent Framework + Gateway in production): https://databricks.com/blog/databricks-databricks-transforming-sales-experience-using-genai-agents

## 7. OWASP risks — every control traces to a named risk
OWASP Top 10 for LLM Applications (2025) is the threat vocabulary. The
mapping is normative for this repo: a control without a risk, or a risk
without an eval case, is a gap.

| OWASP risk (2025) | Control in this repo | Eval case(s) |
|---|---|---|
| LLM01 Prompt Injection | injection-pattern policy scans tool *arguments*; LLM judge as second layer | `prompt-injection-search` |
| LLM02 Sensitive Information Disclosure | sensitive-data policy (secret-shaped payloads); file-access policy (secrets files) | `secret-exfil-email`, `file-secrets` |
| LLM05 Improper Output Handling | calculator is AST-evaluated (no `eval()`); model output never executed raw | `calculator-code-injection` |
| LLM06 Excessive Agency | judge-before-action gate; small curated tool set; per-call human approvals for destructive tools | `shell-needs-approval`, `delete-tmp-needs-approval`, `export-needs-approval`, `delete-prod-path` |
| LLM10 Unbounded Consumption | per-tool/session rate limits; dedupe; bounded retries + `max_steps`; router cost metering | `duplicate-call`, `rate-limit-abuse` |
| (cross-cutting) No accountability | append-only JSONL audit of *every* decision incl. allows | asserted in `tests/test_audit_approvals.py` |

Key OWASP nuance this design respects: prompt injection has no reliable
filter-only fix, so the architecture aims at **containment** -- even a
successful injection meets a gate, a budget, and an approval before it can
become an action.
- OWASP 2025 list summary (LLM01-LLM10): https://www.bestfreewebresources.com/local-llm-security-prompt-injection-2026

## 8. Judge-before-action / learned policy gates
The pattern of a small, fast model (or rule set) scoring a proposed action
*before* execution -- the "System One judge" idea explored by TypeSafe AI's
Jev and by LLM-as-judge evaluation practice generally -- is implemented
here as `Judge`/`CompositeJudge`: rules are the auditable floor, a learned
judge may add strictness, and neither may be talked out of a DENY by the
agent being judged.
