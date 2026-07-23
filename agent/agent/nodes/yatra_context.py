"""yatra_context — resolve which yatra the user is on (Pandharpur/Kumbh).

Like language, the active yatra is persisted statelessly via a [yatra:xx]
marker on assistant turns and re-derived each turn. An explicit switch
phrase ("switch to kumbh") overrides the stored value.
"""
from __future__ import annotations
import re
from langchain_core.messages import AIMessage, HumanMessage

from agent.state import YatraState

_YATRA_MARKER_RE = re.compile(r"\[yatra:(pandharpur|kumbh)\]")

_PANDHARPUR_RE = re.compile(r"pandharpur|wari|warkari|vitthal|palkhi|dehu|alandi|पंढरपूर|वारी|वारकरी|विठ्ठल|पालखी", re.IGNORECASE)
_KUMBH_RE = re.compile(r"kumbh|simhastha|nashik|nasik|trimbak|godavari|सिंहस्थ|कुंभ|नाशिक|त्र्यंबक", re.IGNORECASE)

# Trilingual "which yatra?" ask. Marker [yatra-ask] lets us detect the
# follow-up turn deterministically (stripped before display in Task 8).
_YATRA_ASK = {
    "mr": "[yatra-ask]तुम्ही कोणत्या यात्रेला जात आहात? **पंढरपूर वारी** की **सिंहस्थ कुंभ (नाशिक)**?",
    "hi": "[yatra-ask]आप किस यात्रा पर हैं? **पंढरपुर वारी** या **सिंहस्थ कुंभ (नासिक)**?",
    "en": "[yatra-ask]Which yatra are you on? **Pandharpur Wari** or **Simhastha Kumbh (Nashik)**?",
}


def detect_yatra(text: str) -> str | None:
    if _PANDHARPUR_RE.search(text or ""):
        return "pandharpur"
    if _KUMBH_RE.search(text or ""):
        return "kumbh"
    return None


def _current_yatra(messages) -> str | None:
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            hit = _YATRA_MARKER_RE.search(str(m.content))
            if hit:
                return hit.group(1)
    return None


async def yatra_context(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"

    last_user = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    last_text = str(last_user.content) if last_user else ""

    # Explicit mention in the latest turn always wins (covers switching).
    mentioned = detect_yatra(last_text)
    if mentioned:
        return {**state, "current_node": "yatra_context", "active_yatra": mentioned}  # type: ignore[typeddict-item]

    # Honour a yatra already resolved for this conversation (injected by the
    # webhook from the session store).
    if state.get("active_yatra"):
        return {**state, "current_node": "yatra_context", "active_yatra": state["active_yatra"]}  # type: ignore[typeddict-item]

    # Otherwise carry forward via a marker in history (fallback).
    stored = _current_yatra(messages)
    if stored:
        return {**state, "current_node": "yatra_context", "active_yatra": stored}  # type: ignore[typeddict-item]

    # None chosen yet → ask, and end the turn.
    return {
        **state,
        "current_node": "yatra_context",
        "active_yatra": None,
        "messages": messages + [AIMessage(content=_YATRA_ASK[lang])],
    }
