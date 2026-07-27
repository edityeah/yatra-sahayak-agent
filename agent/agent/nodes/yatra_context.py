"""yatra_context — resolve which yatra the user is on (Pandharpur/Kumbh).

Precedence: an explicit mention in the latest turn ("switch to kumbh") wins,
then the value the webhook's session_store injects into state, then a
best-effort [yatra:xx] marker scan of history (no markers are written today),
else we ask. Plan 2 replaces the store with DB-backed user_state.
"""
from __future__ import annotations
import re
from langchain_core.messages import AIMessage, HumanMessage

from agent.state import YatraState

_YATRA_MARKER_RE = re.compile(r"\[yatra:(pandharpur|kumbh)\]")

_PANDHARPUR_RE = re.compile(r"pandharpur|wari|warkari|vitthal|palkhi|dehu|alandi|पंढरपूर|वारी|वारकरी|विठ्ठल|पालखी", re.IGNORECASE)
_KUMBH_RE = re.compile(r"kumbh|simhastha|nashik|nasik|trimbak|godavari|सिंहस्थ|कुंभ|नाशिक|त्र्यंबक", re.IGNORECASE)

# Tappable choice chips — the webview renders these as buttons and strips the
# token; on SwiftChat they read as the two bold options in the text. Format:
# [[choices:Label::value||Label::value]]
_CHOICES = "[[choices:Pandharpur Wari::pandharpur||Simhastha Kumbh (Nashik)::kumbh]]"

# Trilingual "which yatra?" ask, with the choice chips appended. The
# [yatra-ask] marker (stripped before display) marks the ask deterministically.
_YATRA_ASK = {
    "mr": f"[yatra-ask]तुम्ही कोणत्या यात्रेला जात आहात? खालील पर्याय निवडा:\n\n{_CHOICES}",
    "hi": f"[yatra-ask]आप किस यात्रा पर हैं? नीचे से चुनें:\n\n{_CHOICES}",
    "en": f"[yatra-ask]Which yatra are you on? Pick one below:\n\n{_CHOICES}",
}

# Confirmation shown after a yatra is picked (bare selection turn).
_YATRA_NAME = {
    "pandharpur": {"mr": "पंढरपूर वारी", "hi": "पंढरपुर वारी", "en": "Pandharpur Wari"},
    "kumbh": {"mr": "सिंहस्थ कुंभ (नाशिक)", "hi": "सिंहस्थ कुंभ (नासिक)", "en": "Simhastha Kumbh (Nashik)"},
}
_CONFIRM = {
    "mr": "✅ तुम्ही **{name}** निवडली. हवामान, मार्ग, वाहतूक, हेल्पलाइन, सुरक्षा किंवा नोंदणीबद्दल विचारा. (यात्रा बदलण्यासाठी 'यात्रा बदला' लिहा.)",
    "hi": "✅ आपने **{name}** चुनी। मौसम, मार्ग, परिवहन, हेल्पलाइन, सुरक्षा या पंजीकरण के बारे में पूछें। (यात्रा बदलने के लिए 'यात्रा बदलें' लिखें।)",
    "en": "✅ You're on **{name}**. Ask me about weather, the route, transport, helplines, safety, or registration. (Type 'change yatra' to switch.)",
}

# Words that mean "let me re-pick the yatra".
_CHANGE_RE = re.compile(r"change\s+yatra|switch\s+yatra|different\s+yatra|यात्रा\s*बदल|दुसरी\s*यात्रा|यात्रा\s*बदल", re.IGNORECASE)


def _is_bare_selection(text: str) -> bool:
    """The turn is essentially just a yatra pick (a chip value or a short phrase)."""
    t = (text or "").strip().lower()
    return t in ("pandharpur", "kumbh") or len(t.split()) <= 2


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

    reg_active = bool(state.get("reg_stage")) and state.get("reg_stage") != "done"

    # "change yatra" → clear the selection and re-ask.
    if _CHANGE_RE.search(last_text) and not reg_active:
        return {
            **state, "current_node": "yatra_context", "active_yatra": None,
            "messages": messages + [AIMessage(content=_YATRA_ASK[lang])],
        }

    # Explicit mention in the latest turn wins (covers switching) — UNLESS a
    # registration intake is active, where a yatra-shaped word in an answer
    # (e.g. a Dindi/group name like "Alandi ... Dindi") must not flip the yatra.
    mentioned = detect_yatra(last_text)
    if mentioned and not reg_active:
        # A bare pick (chip tap / one-word answer) → confirm and end the turn so
        # the model doesn't try to route the yatra name itself.
        if _is_bare_selection(last_text):
            name = _YATRA_NAME[mentioned][lang]
            return {
                **state, "current_node": "yatra_context", "active_yatra": mentioned,
                "just_selected_yatra": True,
                "messages": messages + [AIMessage(content=_CONFIRM[lang].format(name=name))],
            }
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
