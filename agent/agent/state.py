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
    just_selected_yatra: bool       # true on the turn the user picks a yatra (→ confirm + end)

    # ── Intent ──────────────────────────────────────────────────────
    intent: Intent

    # ── Webview deep-link context (decoded from ?ctx=… by the webhook) ─
    context_from_webview: dict[str, Any] | None

    # ── Registration intake (multi-turn) ──────────────────────────────
    reg_stage: str | None      # None | name | phone | group | emergency | medical | confirm | done
    reg_fields: dict           # collected fields so far

    # ── Multi-turn "waiting for something" flag (sticky, persisted) ────
    # e.g. "weather_origin" — the weather node asked the user to share a
    # location or name a city, so the NEXT turn (a location message or a
    # bare city name/number) must route back to weather.
    awaiting: str | None

    # ── Native location shared IN CHAT this turn (transient, per-turn) ─
    # {"lat": float, "lng": float} extracted from SwiftChat's location
    # message by the webhook. None on text-only turns.
    shared_location: dict[str, Any] | None

    # ── SOS follow-up: a location shared while awaiting=="sos_location" is a
    # live pin for an OPEN incident (re-route to nearest police control), not a
    # weather origin. Set by the router, consumed by drills_sos. ──────────
    sos_locate: bool


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
        "reg_stage": None,
        "reg_fields": {},
        "awaiting": None,
        "shared_location": None,
        "sos_locate": False,
    }
