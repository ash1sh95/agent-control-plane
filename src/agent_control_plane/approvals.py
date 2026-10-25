"""Human-approval queue, persisted as JSON on disk.

Phone-approval concept: the queue file is the whole contract. Any front end
-- this CLI, a webhook stub (see docs/approval-flow.md), a Telegram/WhatsApp
bot, or a fold-phone dashboard -- only needs to list pending requests and
flip one to approved/denied. The agent never executes a gated call until
that flip happens out-of-band.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path


class ApprovalQueue:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({"pending": [], "decided": {}})

    def _load(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def enqueue(self, tool_name: str, case_id: str, args_hash: str, reason: str) -> str:
        data = self._load()
        req_id = uuid.uuid4().hex[:10]
        data["pending"].append({
            "id": req_id, "tool": tool_name, "case_id": case_id,
            "args_hash": args_hash, "reason": reason, "created_at": time.time(),
        })
        self._save(data)
        return req_id

    def pending(self) -> list[dict]:
        return self._load()["pending"]

    def decide(self, req_id: str, approved: bool) -> bool:
        data = self._load()
        for i, r in enumerate(data["pending"]):
            if r["id"] == req_id:
                data["decided"][req_id] = "approved" if approved else "denied"
                del data["pending"][i]
                self._save(data)
                return True
        return False

    def is_approved(self, req_id: str | None) -> bool:
        if not req_id:
            return False
        return self._load()["decided"].get(req_id) == "approved"
