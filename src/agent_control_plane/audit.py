"""Append-only JSONL audit log: every gate decision, fully attributable."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Decision


class AuditLog:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.records: list[dict] = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, decision: Decision) -> None:
        rec = decision.to_dict()
        self.records.append(rec)
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")

    def for_case(self, case_id: str) -> list[dict]:
        return [r for r in self.records if r["case_id"] == case_id]
