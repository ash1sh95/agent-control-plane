"""MCP adapter (optional, deliberately thin).

Position: governance, not religion. Native function calling is the default
in this repo -- for a small, curated, sensitive tool set it has fewer
moving parts, lower latency, and no extra network/governance surface.
MCP (Model Context Protocol) earns its place when tools must be
*discovered and shared across many agents/hosts*. So MCP is supported at
the boundary, with one non-negotiable rule:

    An MCP-discovered tool is just a proposal source. Its calls are
    converted to ToolCall and pass through the SAME gate. Discovery
    is not trust.

This module maps an MCP-style tool specification (name, description,
inputSchema) into gate known-tools, and MCP `tools/call` payloads into
ToolCall objects. It does not implement an MCP server or client transport
(stdio/SSE) -- that is the stub boundary, clearly labelled in LIMITS.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import ToolCall


@dataclass
class McpToolSpec:
    name: str
    description: str = ""
    input_schema: dict | None = None

    @classmethod
    def from_mcp(cls, spec: dict) -> McpToolSpec:
        return cls(name=spec["name"], description=spec.get("description", ""),
                   input_schema=spec.get("inputSchema"))


class McpToolAdapter:
    """Register MCP-style tools with the gate and translate their calls."""

    def __init__(self, specs: list[dict]):
        self.specs = [McpToolSpec.from_mcp(s) for s in specs]

    @property
    def tool_names(self) -> set[str]:
        return {s.name for s in self.specs}

    def to_tool_call(self, mcp_call: dict, session_id: str, case_id: str) -> ToolCall:
        """Translate an MCP tools/call payload: {name, arguments}."""
        return ToolCall(tool_name=mcp_call["name"], arguments=mcp_call.get("arguments", {}),
                        session_id=session_id, case_id=case_id)

    def describe(self) -> list[dict]:
        """Render specs as OpenAI-style function definitions, so the same
        tool can be offered via native function calling instead -- the two
        transports converge on one governed ToolCall either way."""
        return [{"type": "function", "function": {
            "name": s.name, "description": s.description,
            "parameters": s.input_schema or {"type": "object", "properties": {}}}} for s in self.specs]
