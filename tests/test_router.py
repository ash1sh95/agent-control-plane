from agent_control_plane.router import Router


def test_router_falls_back_and_meters(monkeypatch):
    monkeypatch.delenv("ACP_FRONTIER_API_KEY", raising=False)
    r = Router(ollama_url="http://127.0.0.1:9")  # nothing listening -> local fails fast
    out = r.complete("hello agents")
    assert "frontier-stub" in out
    totals = r.totals()
    assert totals["calls"] == 1 and totals["prompt_tokens"] > 0 and totals["cost_usd"] >= 0

def test_router_accounting_accumulates():
    r = Router()
    r._meter("local-default", "a" * 400, "b" * 400)
    r._meter("local-default", "a" * 400, "b" * 400)
    t = r.totals()
    assert t["calls"] == 2 and t["prompt_tokens"] == 200 and t["cost_usd"] == 0.0  # local is free
