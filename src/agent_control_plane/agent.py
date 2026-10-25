"""Demo agent: proposes tool calls, the gate decides, tools execute.

Uses LangGraph when installed (a real StateGraph: propose -> gate -> act),
and falls back to an identical plain-Python loop when it is not -- the
control plane is the point of this repo, not the orchestration framework.

Bounded behaviour, by design:
- a DENIED call is never retried with identical arguments (that is the
  replanning loop reviewers worry about -- the gate + dedupe make it
  structurally impossible, and max_steps caps the rest);
- transient tool errors retry at most `max_retries` times.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .gate import ControlPlaneGate
from .models import ToolCall, Verdict
from .tools import execute_tool


@dataclass
class AgentResult:
    steps: list[dict] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


def run_plan(gate: ControlPlaneGate, planned_calls: list[ToolCall], max_steps: int = 20,
             max_retries: int = 2) -> AgentResult:
    """Execute a proposed plan through the gate. Used by the demo, the eval
    runner and (as the fallback engine) the LangGraph wrapper."""
    result = AgentResult()
    for call in planned_calls[:max_steps]:
        decision = gate.evaluate(call)
        step = {"tool": call.tool_name, "args_hash": call.hash, "verdict": decision.verdict.value,
                "reason": decision.reason, "policy": decision.policy}
        if decision.verdict != Verdict.ALLOW:
            result.steps.append(step)  # denied / awaiting approval: never executed, never retried as-is
            continue
        for attempt in range(max_retries + 1):
            try:
                out = execute_tool(call.tool_name, call.arguments)
                step["output"] = out
                result.outputs.append(out)
                break
            except Exception as exc:  # noqa: BLE001 - tool errors are data for the step trace, bounded by max_retries
                if attempt == max_retries:
                    step["error"] = f"{type(exc).__name__}: {exc}"
        result.steps.append(step)
    return result


# Deterministic demo planner: maps a plain-English task to tool proposals.
# A real agent replaces this with an LLM -- its proposals still pass the gate.
def plan_for_task(task: str, session_id: str = "demo", case_id: str = "demo-case") -> list[ToolCall]:
    t = task.lower()
    calls: list[ToolCall] = []
    if "calculate" in t or "what is" in t and any(c.isdigit() for c in t):
        expr = "".join(ch for ch in task if ch in "0123456789+-*/(). %")
        if expr.strip():
            calls.append(ToolCall("calculator", {"expression": expr.strip()}, session_id, case_id))
    if "search" in t or "look up" in t or "lookup" in t:
        calls.append(ToolCall("file_lookup", {"query": task}, session_id, case_id))
    if "web" in t:
        calls.append(ToolCall("web_search", {"query": task}, session_id, case_id))
    return calls or [ToolCall("file_lookup", {"query": task}, session_id, case_id)]


def build_langgraph_agent(gate: ControlPlaneGate):
    """Return a compiled LangGraph app, or None if langgraph is absent."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    def gate_node(state):
        call = state["next_call"]
        decision = gate.evaluate(call)
        state["last_decision"] = decision
        return state

    def act_node(state):
        out = execute_tool(state["next_call"].tool_name, state["next_call"].arguments)
        state.setdefault("outputs", []).append(out)
        return state

    def route(state):
        return "act" if state["last_decision"].verdict == Verdict.ALLOW else END

    g = StateGraph(dict)
    g.add_node("gate", gate_node)
    g.add_node("act", act_node)
    g.set_entry_point("gate")
    g.add_conditional_edges("gate", route, {"act": "act", END: END})
    g.add_edge("act", END)
    return g.compile()
