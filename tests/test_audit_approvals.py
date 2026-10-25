import json

from agent_control_plane import ControlPlaneGate, ToolCall
from agent_control_plane.approvals import ApprovalQueue


def test_audit_log_records_every_decision(tmp_path):
    log = tmp_path / "audit.jsonl"
    g = ControlPlaneGate(audit_path=log)
    g.evaluate(ToolCall("calculator", {"expression": "1+1"}, "s", "case-9"))
    g.evaluate(ToolCall("teleport", {}, "s", "case-9"))
    rows = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["case_id"] == "case-9" and rows[1]["verdict"] == "deny"
    assert len(g.audit.for_case("case-9")) == 2

def test_approval_queue_lifecycle(tmp_path):
    q = ApprovalQueue(tmp_path / "approvals.json")
    rid = q.enqueue("shell_command", "case-1", "abc123", "needs a human")
    assert len(q.pending()) == 1 and not q.is_approved(rid)
    assert q.decide(rid, approved=True) and q.is_approved(rid) and q.pending() == []
    assert not q.decide("missing-id", approved=True)

def test_evals_dataset_passes():
    from pathlib import Path

    from agent_control_plane.eval_runner import run_evals
    res = run_evals(Path(__file__).parent.parent / "evals" / "dataset.jsonl")
    assert res["total"] >= 15 and res["false_allows"] == 0 and res["pass_rate"] == 1.0
