"""Add a house rule without touching the gate: policies are just functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agent_control_plane import ControlPlaneGate, ToolCall, Verdict
from agent_control_plane.judge import RuleBasedJudge
from agent_control_plane.policies import DEFAULT_POLICIES, PolicyResult


def no_friday_deploys(call):
    # Example: shell commands mentioning 'deploy' need approval (stricter house rule).
    if call.tool_name == "shell_command" and "deploy" in str(call.arguments):
        return PolicyResult(Verdict.REQUIRE_APPROVAL, "house-rules", "Deploys need a second pair of eyes")
    return None


if __name__ == "__main__":
    gate = ControlPlaneGate(judge=RuleBasedJudge(DEFAULT_POLICIES + [no_friday_deploys]))
    print(gate.evaluate(ToolCall("calculator", {"expression": "1 + 1"}, "s", "c")))
