"""Model router: local-first inference with frontier fallback + accounting.

Local-first is an economics decision, not ideology: agent loops re-send
context many times, so volume belongs on a local model (Ollama / MLX-served,
$0 marginal cost); the frontier model is spent only where local fails or a
task is flagged hard. Every call is metered so "the agent got expensive"
is a queryable fact, not a surprise bill.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field

# USD per 1K tokens (prompt, completion). Local models: electricity only.
PRICES = {"local-default": (0.0, 0.0), "gpt-frontier-stub": (0.005, 0.015)}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class UsageRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@dataclass
class Router:
    local_model: str = "local-default"
    frontier_model: str = "gpt-frontier-stub"
    ollama_url: str = field(default_factory=lambda: os.getenv("ACP_OLLAMA_URL", "http://localhost:11434"))
    usage: list[UsageRecord] = field(default_factory=list)

    def _meter(self, model: str, prompt: str, completion: str) -> UsageRecord:
        pt, ct = estimate_tokens(prompt), estimate_tokens(completion)
        pp, cp = PRICES.get(model, (0.0, 0.0))
        rec = UsageRecord(model, pt, ct, round(pt / 1000 * pp + ct / 1000 * cp, 6))
        self.usage.append(rec)
        return rec

    def _try_local(self, prompt: str) -> str:
        body = json.dumps({"model": os.getenv("ACP_LOCAL_MODEL", "llama3.1:8b"), "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(f"{self.ollama_url}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["response"]

    def _frontier_stub(self, prompt: str) -> str:
        # No real key is ever required in this repo: without ACP_FRONTIER_API_KEY
        # this returns a clearly-labelled stub response instead of calling out.
        if not os.getenv("ACP_FRONTIER_API_KEY"):
            return "[frontier-stub] No ACP_FRONTIER_API_KEY set; this is where a hosted model would answer."
        body = json.dumps({"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {os.environ['ACP_FRONTIER_API_KEY']}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]

    def complete(self, prompt: str, *, hard: bool = False) -> str:
        """Route: local first (unless `hard`), frontier on failure/fallback."""
        if not hard:
            try:
                out = self._try_local(prompt)
                self._meter(self.local_model, prompt, out)
                return out
            except Exception:  # noqa: BLE001, S110 - any local-backend failure must fall back, never crash the agent
                pass  # fall through to frontier
        out = self._frontier_stub(prompt)
        self._meter(self.frontier_model, prompt, out)
        return out

    def totals(self) -> dict:
        return {
            "calls": len(self.usage),
            "prompt_tokens": sum(u.prompt_tokens for u in self.usage),
            "completion_tokens": sum(u.completion_tokens for u in self.usage),
            "cost_usd": round(sum(u.cost_usd for u in self.usage), 6),
            "by_model": {m: sum(1 for u in self.usage if u.model == m) for m in {u.model for u in self.usage}},
        }
