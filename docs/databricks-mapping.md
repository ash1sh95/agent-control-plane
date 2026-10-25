# Mapping to an enterprise Databricks deployment

This repo is a standalone, local-first reference implementation. Every
component has a direct enterprise analogue — the patterns transfer, the
demo tools are the only thing you replace. (Generic patterns only; no
employer systems, data, or code.)

| This repo | Enterprise / Databricks analogue |
|---|---|
| Demo tools (`tools.py`) | **Unity Catalog functions** wrapping governed REST APIs / tables as agent tools |
| Gate in front of tool execution | Agent-framework middleware / custom tool wrapper in your agent code |
| Rule policies | Org policy-as-code, reviewed like any other production change |
| LLM judge (Ollama/frontier) | A small **Foundation Model API** / Model Serving endpoint as judge-before-action |
| Approval queue (JSON file) | Databricks App / Teams / Slack approval with state in a **Delta table** |
| Audit log (JSONL) | **Delta table** in Unity Catalog + **MLflow tracing** for the full run graph |
| Rate limiter (in-process) | Per-case budgets in the executor, with **Azure APIM quotas as the downstream backstop** for the underlying APIs |
| Router + cost accounting | **AI Gateway** usage tracking / inference tables; local-vs-hosted split becomes endpoint-vs-endpoint routing |
| Eval harness (JSONL) | **MLflow evaluations** / agent evaluation datasets run in CI and on deployment |

Three lessons that survive the translation:
1. **Layered control beats any single layer** — executor budgets, a judge
   gate, *and* an API-gateway backstop fail independently.
2. **Audit is a table, not a log file mindset** — every decision queryable
   by case, tool, policy and verdict is what makes incident review possible.
3. **Keep the tool surface small and curated** — four well-governed tools
   beat a registry of forty exposed ones, for both safety and model accuracy.
