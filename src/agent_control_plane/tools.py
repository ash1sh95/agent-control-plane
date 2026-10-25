"""Harmless demo tools. In production these are the *only* surface that
changes: swap these functions for Unity Catalog functions / REST wrappers
and the gate, audit and eval layers stay exactly the same.
"""
from __future__ import annotations

import ast
import operator

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand)
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    """Safe arithmetic: AST-evaluated, no eval(), no names, no calls."""
    return str(_eval(ast.parse(expression, mode="eval")))


# Tiny built-in document set for the RAG-flavoured lookup demo.
_DOCS = {
    "handbook.md": "Agent handbook: agents must pass the control-plane gate before any tool call. Rate limits are per session.",
    "travel.md": "Travel policy: book refundable fares. Approvals are required for purchases over $500.",
    "oncall.md": "On-call runbook: check the audit log first. Every gate decision is in audit.jsonl with its case id.",
}


def file_lookup(query: str, path: str = "") -> str:
    """Keyword lookup over the built-in demo corpus (stand-in for a vector
    store / UC table). Path arguments are validated by the gate, not here."""
    q = query.lower()
    hits = [f"{name}: {text}" for name, text in _DOCS.items() if q in text.lower() or q in name]
    return "\n".join(hits) if hits else f"No documents matched '{query}'."


_SEARCH_INDEX = {
    "databricks": "Databricks: unified data & AI platform; Mosaic AI for agents, Unity Catalog for governance.",
    "langgraph": "LangGraph: graph-based agent orchestration with state, checkpoints and human-in-the-loop.",
    "ollama": "Ollama: local LLM serving with an OpenAI-compatible API; common local-first backend.",
}


def web_search(query: str) -> str:
    """Offline search stub over a canned index -- deterministic for demos
    and evals, and honest about being a stub. Swap for a real search API
    behind the same gate in production."""
    q = query.lower()
    for key, text in _SEARCH_INDEX.items():
        if key in q:
            return text
    return f"[search-stub] No canned result for '{query}'. A live search API would be called here."


TOOL_REGISTRY = {"calculator": calculator, "file_lookup": file_lookup, "web_search": web_search}


def execute_tool(name: str, arguments: dict) -> str:
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Tool '{name}' has no local executor (gated enterprise tools are not executed in the demo)")
    return TOOL_REGISTRY[name](**arguments)
