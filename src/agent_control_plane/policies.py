"""Declarative rule policies, evaluated by the rule-based judge.

Order matters only for the human-readable reason: the gate aggregates all
policy results and applies the strictest verdict (deny > approval > allow),
so authors never have to reason about rule ordering for safety.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ToolCall, Verdict

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"bypass (the )?(policy|gate|approval)",
    r"disregard (your )?(rules|policy)",
    r"exfiltrate",
    r"you are now (in )?(developer|god|dan) mode",
]
SENSITIVE_PATTERNS = [r"password\s*[:=]", r"api[_-]?key\s*[:=]", r"\bssn\b", r"social security", r"credit card\s*[:=]"]
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org"}  # stand-ins for an org allowlist


@dataclass
class PolicyResult:
    verdict: Verdict
    policy: str
    reason: str


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _all_strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _all_strings(v)


def injection_policy(call: ToolCall) -> PolicyResult | None:
    text = " ".join(_all_strings(call.arguments)).lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, text):
            return PolicyResult(Verdict.DENY, "prompt-injection", f"Argument matched injection pattern: {pat}")
    return None


def sensitive_data_policy(call: ToolCall) -> PolicyResult | None:
    text = " ".join(_all_strings(call.arguments)).lower()
    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, text):
            return PolicyResult(Verdict.DENY, "sensitive-data", f"Argument appears to carry a secret/PII payload: {pat}")
    return None


def tool_risk_policy(call: ToolCall) -> PolicyResult | None:
    tool, args = call.tool_name, call.arguments
    if tool == "shell_command":
        return PolicyResult(Verdict.REQUIRE_APPROVAL, "tool-risk", "Shell execution always requires human approval")
    if tool == "delete_file":
        path = str(args.get("path", ""))
        if "/prod" in path or path.startswith("/etc") or "production" in path:
            return PolicyResult(Verdict.DENY, "tool-risk", f"Refusing to delete a production/system path: {path}")
        return PolicyResult(Verdict.REQUIRE_APPROVAL, "tool-risk", "File deletion requires human approval")
    if tool == "export_data":
        return PolicyResult(Verdict.REQUIRE_APPROVAL, "tool-risk", "Data export requires human approval")
    if tool == "send_email":
        to = str(args.get("to", ""))
        domain = to.rsplit("@", 1)[-1].lower() if "@" in to else ""
        if domain not in ALLOWED_EMAIL_DOMAINS:
            return PolicyResult(Verdict.REQUIRE_APPROVAL, "tool-risk", f"External recipient domain requires approval: {domain or to}")
    return None


def file_access_policy(call: ToolCall) -> PolicyResult | None:
    if call.tool_name != "file_lookup":
        return None
    path = str(call.arguments.get("path", "")) + str(call.arguments.get("query", ""))
    if ".." in path or path.startswith(("/", "~")):
        return PolicyResult(Verdict.DENY, "file-access", "Path traversal / absolute paths are not allowed")
    if any(s in path.lower() for s in ("secret", ".env", "credential", "id_rsa")):
        return PolicyResult(Verdict.DENY, "file-access", "Refusing access to a secrets-looking file")
    return None


def calculator_policy(call: ToolCall) -> PolicyResult | None:
    if call.tool_name != "calculator":
        return None
    expr = str(call.arguments.get("expression", ""))
    if not re.fullmatch(r"[0-9+\-*/(). %]+", expr.strip() or " "):
        return PolicyResult(Verdict.DENY, "calculator-safety", "Expression contains characters outside arithmetic")
    return None


DEFAULT_POLICIES = [injection_policy, sensitive_data_policy, tool_risk_policy, file_access_policy, calculator_policy]
