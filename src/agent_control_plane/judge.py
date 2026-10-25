"""Judges: who decides allow / deny / require-approval for a tool call.

RuleBasedJudge is deterministic, unit-testable, and is the default -- for a
control plane this is a feature: safety decisions should be reproducible and
auditable, not vibes. LLMJudge is the pluggable interface for a learned
judge-before-action layer (the Jev / "System One" pattern): a small fast
model scores the call, and its verdict is *combined* with the rules, never
allowed to override a rule-based DENY.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol

from .models import ToolCall, Verdict
from .policies import DEFAULT_POLICIES, PolicyResult

_STRICTNESS = {Verdict.ALLOW: 0, Verdict.REQUIRE_APPROVAL: 1, Verdict.DENY: 2}


def strictest(results: list[PolicyResult]) -> PolicyResult:
    return max(results, key=lambda r: _STRICTNESS[r.verdict])


class Judge(Protocol):
    def evaluate(self, call: ToolCall) -> PolicyResult: ...


class RuleBasedJudge:
    def __init__(self, policies=None):
        self.policies = policies if policies is not None else DEFAULT_POLICIES

    def evaluate(self, call: ToolCall) -> PolicyResult:
        hits = [r for p in self.policies if (r := p(call)) is not None]
        if not hits:
            return PolicyResult(Verdict.ALLOW, "default-allow", "No policy objected")
        return strictest(hits)


class LLMJudge:
    """LLM-judge interface with two backends. Both are stubs by design:
    no keys ship in this repo, and a transport failure *fails closed*
    (require-approval) rather than allowing the call.

    - backend="ollama": POSTs to a local Ollama server (default model from
      ACP_JUDGE_MODEL, e.g. a small Qwen/Llama) -- local-first.
    - backend="frontier": OpenAI-compatible endpoint, key from
      ACP_FRONTIER_API_KEY. Wired for teams that want a hosted judge.
    """

    SYSTEM = ("You are a policy judge for an AI agent. Given a tool call, reply with ONLY JSON: "
              '{"verdict": "allow|deny|require_approval", "reason": "..."}')

    def __init__(self, backend: str = "ollama", model: str | None = None, base_url: str | None = None):
        self.backend = backend
        self.model = model or os.getenv("ACP_JUDGE_MODEL", "llama3.1:8b")
        self.base_url = base_url or os.getenv("ACP_OLLAMA_URL", "http://localhost:11434")

    def _prompt(self, call: ToolCall) -> str:
        return f"Tool: {call.tool_name}\nArguments: {json.dumps(call.arguments, default=str)}\nCase: {call.case_id}"

    def evaluate(self, call: ToolCall) -> PolicyResult:
        try:
            if self.backend == "ollama":
                body = json.dumps({"model": self.model, "stream": False,
                                   "messages": [{"role": "system", "content": self.SYSTEM},
                                                {"role": "user", "content": self._prompt(call)}]}).encode()
                req = urllib.request.Request(f"{self.base_url}/api/chat", data=body,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = json.loads(resp.read())["message"]["content"]
            else:  # frontier, OpenAI-compatible
                key = os.environ["ACP_FRONTIER_API_KEY"]  # KeyError -> fail closed below
                body = json.dumps({"model": self.model,
                                   "messages": [{"role": "system", "content": self.SYSTEM},
                                                {"role": "user", "content": self._prompt(call)}]}).encode()
                req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                                             headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    text = json.loads(resp.read())["choices"][0]["message"]["content"]
            parsed = json.loads(text[text.index("{"):text.rindex("}") + 1])
            return PolicyResult(Verdict(parsed["verdict"]), f"llm-judge:{self.backend}", parsed.get("reason", ""))
        except Exception as exc:  # noqa: BLE001 - fail closed, never open: any judge error becomes require-approval
            return PolicyResult(Verdict.REQUIRE_APPROVAL, f"llm-judge:{self.backend}",
                                f"Judge unavailable ({type(exc).__name__}); failing closed to human approval")


class CompositeJudge:
    """Rules first, LLM second; strictest verdict wins, rules can never be
    talked out of a DENY by a model."""

    def __init__(self, rule_judge: RuleBasedJudge, llm_judge: LLMJudge | None = None):
        self.rule_judge, self.llm_judge = rule_judge, llm_judge

    def evaluate(self, call: ToolCall) -> PolicyResult:
        base = self.rule_judge.evaluate(call)
        if base.verdict == Verdict.DENY or self.llm_judge is None:
            return base
        return strictest([base, self.llm_judge.evaluate(call)])
