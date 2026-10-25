from agent_control_plane.rate_limiter import RateLimiter


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t

def test_limit_enforced_per_tool_and_session():
    rl = RateLimiter({"calculator": 2, "*": 5}, clock=Clock())
    for _ in range(2): assert rl.check("s", "calculator"); rl.record("s", "calculator")
    assert not rl.check("s", "calculator")
    assert rl.check("other-session", "calculator")  # sessions are isolated
    assert rl.check("s", "web_search")

def test_window_expires():
    clk = Clock(); rl = RateLimiter({"*": 1}, window_seconds=60, clock=clk)
    rl.record("s", "calculator"); assert not rl.check("s", "calculator")
    clk.t += 61; assert rl.check("s", "calculator")
