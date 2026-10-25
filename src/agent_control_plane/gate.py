"""The control-plane gate: the single choke point every tool call passes.

Evaluation order (defense in depth, cheapest checks first):
  1. Known-tool check        -> unknown tools are denied outright
  2. Duplicate-call check    -> same tool+args already ran in this case
  3. Rate-limit check        -> per-tool, per-session budget
  4. Judge (rules / LLM)     -> policy verdict
  5. Approval                -> REQUIRE_APPROVAL calls are queued, not run
Every outcome -- including allows -- is written to the audit log.
"""
from __future__ import annotations

from pathlib import Path

from .approvals import ApprovalQueue
from .audit import AuditLog
from .dedupe import DedupeStore
from .judge import RuleBasedJudge
from .models import Decision, ToolCall, Verdict
from .rate_limiter import RateLimiter

KNOWN_TOOLS = {"calculator", "file_lookup", "web_search", "send_email", "delete_file", "shell_command", "export_data"}


class ControlPlaneGate:
    def __init__(self, judge=None, rate_limits: dict | None = None, audit_path=None,
                 approval_path=None, known_tools=None):
        self.judge = judge or RuleBasedJudge()
        self.rate_limiter = RateLimiter(rate_limits or {"calculator": 10, "web_search": 10, "file_lookup": 10, "*": 5})
        self.dedupe = DedupeStore()
        self.audit = AuditLog(audit_path)
        self.approvals = ApprovalQueue(approval_path) if approval_path else None
        self.known_tools = known_tools or KNOWN_TOOLS
        self._tmp_approval = None  # lazily-created temp queue when no path given

    def _decision(self, call: ToolCall, verdict, reason, policy, approval_id=None) -> Decision:
        d = Decision(verdict=verdict, reason=reason, policy=policy, tool_name=call.tool_name,
                     case_id=call.case_id, session_id=call.session_id, args_hash=call.hash,
                     approval_id=approval_id)
        self.audit.log(d)
        return d

    def evaluate(self, call: ToolCall, *, record: bool = True) -> Decision:
        if call.tool_name not in self.known_tools:
            return self._decision(call, Verdict.DENY, f"Unknown tool: {call.tool_name}", "known-tools")
        if self.dedupe.seen(call.case_id, call.session_id, call.hash):
            return self._decision(call, Verdict.DENY, "Duplicate call: identical tool+args already executed in this case", "dedupe")
        if not self.rate_limiter.check(call.session_id, call.tool_name):
            return self._decision(call, Verdict.DENY,
                                  f"Rate limit exceeded for {call.tool_name} in session {call.session_id}", "rate-limit")
        result = self.judge.evaluate(call)
        approval_id = None
        if result.verdict == Verdict.REQUIRE_APPROVAL:
            queue = self.approvals
            if queue is None:
                if self._tmp_approval is None:
                    import tempfile
                    self._tmp_approval = ApprovalQueue(Path(tempfile.mkdtemp()) / "approvals.json")
                queue = self._tmp_approval
            approval_id = queue.enqueue(call.tool_name, call.case_id, call.hash, result.reason)
        decision = self._decision(call, result.verdict, result.reason, result.policy, approval_id)
        if decision.allowed and record:
            # Only *executed* (allowed) calls consume budget / dedupe slots;
            # a denied call must not poison later legitimate retries.
            self.rate_limiter.record(call.session_id, call.tool_name)
            self.dedupe.record(call.case_id, call.session_id, call.hash)
        return decision
