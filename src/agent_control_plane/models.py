"""Core data models for the control plane."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


def args_hash(tool_name: str, arguments: dict) -> str:
    """Stable hash of a tool call's arguments (canonical JSON, sorted keys)."""
    payload = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict = field(default_factory=dict)
    session_id: str = "default-session"
    case_id: str = "default-case"
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def hash(self) -> str:
        return args_hash(self.tool_name, self.arguments)

    def to_dict(self) -> dict:
        return {**asdict(self), "args_hash": self.hash}


@dataclass
class Decision:
    verdict: Verdict
    reason: str
    policy: str = "default"
    tool_name: str = ""
    case_id: str = ""
    session_id: str = ""
    args_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    approval_id: str | None = None

    @property
    def allowed(self) -> bool:
        return self.verdict == Verdict.ALLOW

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d
