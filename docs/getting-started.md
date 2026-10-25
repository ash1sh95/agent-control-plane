# Getting started

## 60-second local tour
```bash
pip install -e .
acp demo     # watch allows, denials, and one approval happen, with reasons
acp eval     # 17/17 gate exam
acp audit    # last decisions from the audit log
pytest -q    # 19 tests
```

## Add your first tool safely (the whole workflow)
1. Write the tool function in `tools.py` and add it to `TOOL_REGISTRY`
   and to the gate's `KNOWN_TOOLS` (unknown tools are denied by default).
2. Ask: what is the worst call an injected agent could propose to it?
   Write that as an eval case in `evals/dataset.jsonl` first.
3. Add/extend a policy in `policies.py` until the case passes -- one
   function, strictest-verdict aggregation does the rest.
4. Run `make test && make eval`. Both green = your tool is governed.

## Turn on a local LLM judge (optional)
```bash
ollama pull gpt-oss:20b        # or qwen3-coder:30b on a 32GB+ machine
export ACP_JUDGE_MODEL=gpt-oss:20b
```
Wire `CompositeJudge(RuleBasedJudge(), LLMJudge())` where you construct
the gate. Remember: it can only make verdicts *stricter*, and it fails
closed if Ollama is down.

## Approve from your phone
The approval queue is a file contract: `acp approvals list`,
`acp approvals approve <id>`. Any phone-reachable front end (dashboard,
chat bot, webhook -- see `docs/approval-flow.md`) flips the same state.
