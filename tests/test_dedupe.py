from agent_control_plane import ControlPlaneGate, ToolCall, Verdict


def test_duplicate_blocked_same_case_only():
    g = ControlPlaneGate()
    call = ToolCall("calculator", {"expression": "7 * 6"}, "s", "case-a")
    assert g.evaluate(call).verdict == Verdict.ALLOW
    assert g.evaluate(call).verdict == Verdict.DENY
    other_case = ToolCall("calculator", {"expression": "7 * 6"}, "s", "case-b")
    assert g.evaluate(other_case).verdict == Verdict.ALLOW  # different case: legitimate

def test_different_args_not_duplicate():
    g = ControlPlaneGate()
    assert g.evaluate(ToolCall("calculator", {"expression": "1+1"}, "s", "c")).allowed
    assert g.evaluate(ToolCall("calculator", {"expression": "2+2"}, "s", "c")).allowed
