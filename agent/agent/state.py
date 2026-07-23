"""YatraState — TypedDict carried through the LangGraph spine.

Every node returns a full state dict ({**state, ...updates}). Nodes are
stateless per request; anything that must persist is re-derived from the
message history or the DB, mirroring swift-learning-agent.
"""
from __future__ import annotations
from typing import Any, Literal, TypedDict
from langchain_core.messages import BaseMessage

# The two yatras this POC covers (spec §1.4).
YATRAS = ("pandharpur", "kumbh")
# Supported languages: Marathi, Hindi, English.
LANGS = ("mr", "hi", "en")

Yatra = Literal["pandharpur", "kumbh"]
Lang = Literal["mr", "hi", "en"]

# The activities the router can dispatch to (spec §5).
Intent = Literal[
    "browse",         # greeting / language or yatra selection / menu
    "weather",
    "advisory",
    "logistics",
    "helpline",
    "drills_sos",
    "signage",
    "registration",
    "answer",         # generic on-topic answer already written by the router
    "off_topic",      # politely redirect
]


class YatraState(TypedDict, total=False):
    # ── Routing / meta ──────────────────────────────────────────────
    messages: list[BaseMessage]
    session_id: str
    user_id: str
    current_node: str
    policy_result: Literal["allowed", "blocked"]
    block_reason: str
    sos: bool                       # set by content_policy SOS tripwire

    # ── Selections ──────────────────────────────────────────────────
    language: Lang | None           # None until the user picks one
    active_yatra: Yatra | None      # None until the user picks one

    # ── Intent ──────────────────────────────────────────────────────
    intent: Intent

    # ── Webview deep-link context (decoded from ?ctx=… by the webhook) ─
    context_from_webview: dict[str, Any] | None


def new_state(session_id: str, user_id: str) -> YatraState:
    return {
        "messages": [],
        "session_id": session_id,
        "user_id": user_id,
        "current_node": "start",
        "policy_result": "allowed",
        "block_reason": "",
        "sos": False,
        "language": None,
        "active_yatra": None,
        "intent": "browse",
        "context_from_webview": None,
    }
