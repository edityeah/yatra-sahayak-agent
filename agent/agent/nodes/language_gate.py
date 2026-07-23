"""language_gate — pick language once, then mirror it every turn.

Sets state['language'] to 'mr' | 'hi' | 'en'. On a fresh thread with no
prior assistant turn, appends the selection prompt and leaves language=None
(the graph ends the turn there). Once chosen, the language is re-derived
from the [lang:xx] marker on the earliest post-selection assistant turn.
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
    """Earliest recorded language marker in the assistant history."""
    for m in messages:
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

    # Already chosen earlier in the thread → carry it forward.
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
