from agent_control_plane import ControlPlaneGate, Verdict
from agent_control_plane.mcp_adapter import McpToolAdapter

SPECS = [{"name": "calculator", "description": "Arithmetic", "inputSchema": {"type": "object"}},
         {"name": "file_lookup", "description": "Docs lookup", "inputSchema": {"type": "object"}}]

def test_mcp_call_translates_and_is_gated():
    adapter = McpToolAdapter(SPECS)
    call = adapter.to_tool_call({"name": "file_lookup", "arguments": {"query": "x", "path": "../.env"}}, "s", "c")
    gate = ControlPlaneGate(known_tools=adapter.tool_names)
    assert gate.evaluate(call).verdict == Verdict.DENY  # discovery is not trust: traversal still blocked

def test_mcp_specs_render_as_native_functions():
    fns = McpToolAdapter(SPECS).describe()
    assert fns[0]["type"] == "function" and fns[1]["function"]["name"] == "file_lookup"
