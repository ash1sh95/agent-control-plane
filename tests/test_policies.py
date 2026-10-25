from agent_control_plane import ToolCall, Verdict
from agent_control_plane.judge import LLMJudge, RuleBasedJudge

J = RuleBasedJudge()
C = lambda tool, args: ToolCall(tool, args, "s", "c")

def test_file_traversal_and_secrets_denied():
    assert J.evaluate(C("file_lookup", {"path": "../x", "query": "y"})).verdict == Verdict.DENY
    assert J.evaluate(C("file_lookup", {"path": "app/.env", "query": "y"})).verdict == Verdict.DENY

def test_prod_delete_denied_tmp_delete_approval():
    assert J.evaluate(C("delete_file", {"path": "/prod/db"})).verdict == Verdict.DENY
    assert J.evaluate(C("delete_file", {"path": "/tmp/x"})).verdict == Verdict.REQUIRE_APPROVAL

def test_llm_judge_fails_closed_without_server():
    d = LLMJudge(backend="ollama", base_url="http://127.0.0.1:9").evaluate(C("calculator", {"expression": "1+1"}))
    assert d.verdict == Verdict.REQUIRE_APPROVAL  # unavailable judge must never allow
