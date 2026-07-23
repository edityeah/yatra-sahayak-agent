"""language_gate — pick language once, then keep it for the conversation.

Sets state['language'] to 'mr' | 'hi' | 'en'. On a fresh thread it appends
the selection prompt and leaves language=None (the graph ends the turn).
Persistence across turns is provided by the webhook's session_store, which
injects the resolved language back into state; when it's already set we
honour it and skip the ask. The [lang:xx] marker scan below is only a
best-effort fallback for histories that happen to carry such a marker (none
are written today). Plan 2 replaces the store with DB-backed user_state.
"""
from __future__ import annotations
import re
from langchain_core.messages import AIMessage, HumanMessage

from agent.state import YatraState
from agent.i18n import (
    language_selection_text,
    detect_language_choice,
    LANG_ASK_MARKER,
)

_LANG_MARKER_RE = re.compile(r"\[lang:(mr|hi|en)\]")


def _current_language(messages) -> str | None:
    """Most-recent recorded language marker in the assistant history."""
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            hit = _LANG_MARKER_RE.search(str(m.content))
            if hit:
                return hit.group(1)
    return None


def _asked_language(messages) -> bool:
    ai = [m for m in messages if isinstance(m, AIMessage) and str(m.content).strip()]
    return bool(ai) and LANG_ASK_MARKER in str(ai[-1].content)


def _is_fresh_thread(messages) -> bool:
    return not any(isinstance(m, AIMessage) and str(m.content).strip() for m in messages)


async def language_gate(state: YatraState) -> YatraState:
    messages = state.get("messages") or []

    # Honour a language already resolved for this conversation (injected by the
    # webhook from the session store) — don't re-ask.
    if state.get("language"):
        return {**state, "current_node": "language_gate", "language": state["language"]}  # type: ignore[typeddict-item]

    # Else re-derive from a marker in history (fallback).
    lang = _current_language(messages)
    if lang:
        return {**state, "current_node": "language_gate", "language": lang}  # type: ignore[typeddict-item]

    last_user = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    last_text = str(last_user.content).strip() if last_user else ""

    # We just asked → try to parse their choice.
    if _asked_language(messages):
        picked = detect_language_choice(last_text)
        if picked:
            return {**state, "current_node": "language_gate", "language": picked}  # type: ignore[typeddict-item]
        # Unparseable → default to English and proceed (never get stuck).
        return {**state, "current_node": "language_gate", "language": "en"}

    # Fresh thread → ask. End the turn with the selection prompt.
    if _is_fresh_thread(messages):
        return {
            **state,
            "current_node": "language_gate",
            "language": None,
            "messages": messages + [AIMessage(content=language_selection_text())],
        }

    # Mid-thread but no marker (e.g. legacy) → default English.
    return {**state, "current_node": "language_gate", "language": "en"}
