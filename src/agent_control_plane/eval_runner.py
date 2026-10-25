"""Eval harness: does the gate make the *right* decision, measurably?

Each JSONL case declares a tool call (plus optional setup calls that run
first -- that is how duplicate and rate-limit abuse are tested) and the
expected verdict. Reported metrics:
- pass rate          : exact verdict matches / total
- false allows       : expected deny/approval, gate allowed  (the dangerous one)
- false denies       : expected allow, gate blocked it       (the annoying one)
"""
from __future__ import annotations

import json
from pathlib import Path

from .gate import ControlPlaneGate
from .models import ToolCall, Verdict


def _call(spec: dict) -> ToolCall:
    return ToolCall(spec["tool"], spec.get("arguments", {}),
                    spec.get("session_id", "eval-session"), spec.get("case_id", "eval-case"))


def run_evals(dataset_path: str | Path, rate_limits: dict | None = None, verbose: bool = False) -> dict:
    cases = [json.loads(l) for l in Path(dataset_path).read_text().splitlines() if l.strip()]
    rows, false_allows, false_denies = [], 0, 0
    for case in cases:
        gate = ControlPlaneGate(rate_limits=rate_limits or {"calculator": 5, "web_search": 5, "file_lookup": 5, "*": 5})
        for setup in case.get("setup", []):
            gate.evaluate(_call({**setup, "session_id": case.get("session_id", "eval-session"),
                                 "case_id": case.get("case_id", case["id"])}))
        decision = gate.evaluate(_call({**case, "case_id": case["id"]}))
        expected = Verdict(case["expected"])
        ok = decision.verdict == expected
        if not ok and decision.verdict == Verdict.ALLOW:
            false_allows += 1
        if not ok and expected == Verdict.ALLOW:
            false_denies += 1
        rows.append({"id": case["id"], "category": case.get("category", ""), "expected": expected.value,
                     "got": decision.verdict.value, "pass": ok, "reason": decision.reason})
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {case['id']:<28} expected={expected.value:<18} got={decision.verdict.value}")
    passed = sum(r["pass"] for r in rows)
    return {"total": len(rows), "passed": passed, "pass_rate": round(passed / max(1, len(rows)), 3),
            "false_allows": false_allows, "false_denies": false_denies, "rows": rows}


def format_summary(result: dict) -> str:
    lines = ["=" * 62, "AGENT CONTROL PLANE - EVAL SUMMARY", "=" * 62,
             f"{'Case':<28}{'Expected':<18}{'Got':<18}{'Result'}", "-" * 62]
    for r in result["rows"]:
        lines.append(f"{r['id']:<28}{r['expected']:<18}{r['got']:<18}{'PASS' if r['pass'] else 'FAIL'}")
    lines += ["-" * 62,
              f"Pass rate : {result['passed']}/{result['total']} = {result['pass_rate']:.1%}",
              f"False allows (dangerous): {result['false_allows']}",
              f"False denies (friction) : {result['false_denies']}"]
    return "\n".join(lines)
