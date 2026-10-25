# Changelog
All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions use SemVer.

## [0.1.0] - 2026-10-25
### Added
- Judge-before-action gate: known-tool, dedupe, rate-limit, policy-judge
  and human-approval stages, in that order, all audited to JSONL.
- Rule policies mapped to OWASP LLM risks (injection, sensitive data,
  excessive agency, unbounded consumption, output handling).
- Pluggable judges: rule-based (default), LLM judge (Ollama / frontier,
  fail-closed), composite (strictest wins).
- Local-first model router with token/cost accounting.
- LangGraph agent wrapper with plain-loop fallback; bounded retries/steps.
- MCP adapter: MCP-style tool specs/calls governed by the same gate.
- Decision-level eval harness: 17 cases, CI fails on any false allow.
- Databricks pack: notebook (MLflow + Delta results), Asset Bundle
  skeleton, Model Serving gate example, 10-minute guide.
- Demo CLI (`acp demo|eval|approvals|audit`), Docker + compose, CI.
