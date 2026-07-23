"""In-memory per-conversation store for the resolved language + active yatra.

POC-only: survives within a single running process, NOT across restarts or
multiple instances. It exists because the webhook strips internal markers
before streaming, so the chosen language/yatra can't ride back in the client
history. Plan 2 replaces this with DB-backed `user_state` for durability.
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
    language: str | None = None,
    active_yatra: str | None = None,
) -> None:
    cur = _STORE.setdefault(conversation_id, {})
    if messages is not None:
        cur["messages"] = messages
    if language is not None:
        cur["language"] = language
    if active_yatra is not None:
        cur["active_yatra"] = active_yatra


def clear(conversation_id: str) -> None:
    _STORE.pop(conversation_id, None)
