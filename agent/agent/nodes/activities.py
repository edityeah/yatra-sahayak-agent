"""Stub activity nodes — one per NDMA activity (spec §5).

Each returns a placeholder reply so the spine is testable end-to-end.
Plan 2 replaces each body with the real implementation. The function
signatures and node names are FINAL — the graph binds to these.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState

_STUB = {
    "weather":      "🌦️ [weather] Route-wise forecast will appear here (IMD, live). — Plan 2.",
    "advisory":     "📢 [advisory] District advisories & road closures will appear here. — Plan 2.",
    "logistics":    "🐎 [logistics] Govt-notified pony/transport rates + providers. — Plan 2.",
    "helpline":     "☎️ [helpline] One-tap 112 / 108 / control-room dialling. — Plan 2.",
    "drills_sos":   "🆘 [drills_sos] Preparedness drills + live SOS to the control room. — Plan 2.",
    "signage":      "🧭 [signage] Route map + turn-by-turn signage layer. — Plan 2.",
    "registration": "🪪 [registration] Simulated e-KYC → QR yatra pass. — Plan 2.",
}


def _make(name: str):
    async def _node(state: YatraState) -> YatraState:
        messages = state.get("messages") or []
        return {
            **state,
            "current_node": name,
            "messages": messages + [AIMessage(content=_STUB[name])],
        }
    _node.__name__ = name
    return _node


ACTIVITY_NODES = {name: _make(name) for name in _STUB}
