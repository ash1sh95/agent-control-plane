"""Duplicate-call prevention: same tool + same args in a case/session is blocked.

Motivation (a real reviewer concern on enterprise agents): an LLM in a
replanning loop can invoke the same tool with identical arguments repeatedly,
burning API quota and duplicating side effects. We key on case+session so the
same call in a *different* case remains legitimate.
"""
from __future__ import annotations


class DedupeStore:
    def __init__(self):
        self._seen: set[tuple[str, str, str]] = set()  # (case_id, session_id, hash)

    def seen(self, case_id: str, session_id: str, call_hash: str) -> bool:
        return (case_id, session_id, call_hash) in self._seen

    def record(self, case_id: str, session_id: str, call_hash: str) -> None:
        self._seen.add((case_id, session_id, call_hash))

    def clear_session(self, session_id: str) -> None:
        self._seen = {k for k in self._seen if k[1] != session_id}
