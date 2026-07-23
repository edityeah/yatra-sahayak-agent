"""In-memory per-conversation store: the transcript + any in-progress
registration intake (reg_stage / reg_fields). Conversation-scoped (keyed by
conversation_id) so a new chat never inherits another conversation's intake.

Language and active_yatra are deliberately USER-scoped and live in the
persistence layer, not here.

POC-only: single process, not concurrency-safe for simultaneous requests on
the same conversation_id (last write wins), transcript grows unbounded (no
TTL/cap). Plans 3–4 move durable state to the DB.
"""
from __future__ import annotations
from typing import Any

_STORE: dict[str, dict[str, Any]] = {}


def load(conversation_id: str) -> dict[str, Any]:
    return dict(_STORE.get(conversation_id, {}))


def save(
    conversation_id: str,
    *,
    messages: list | None = None,
    reg_stage: str | None = None,
    reg_fields: dict | None = None,
    reply_language: str | None = None,
) -> None:
    cur = _STORE.setdefault(conversation_id, {})
    if messages is not None:
        cur["messages"] = messages
    if reg_stage is not None:
        cur["reg_stage"] = reg_stage
    if reg_fields is not None:
        cur["reg_fields"] = reg_fields
    if reply_language is not None:
        cur["reply_language"] = reply_language


def clear(conversation_id: str) -> None:
    _STORE.pop(conversation_id, None)
