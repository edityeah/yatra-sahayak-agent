"""intent_router — classify the turn into one activity intent.

SOS turns (state['sos']=True) skip the LLM and route straight to
drills_sos. Otherwise a structured-output RouteDecision picks one of the
activity intents. For browse/answer/off_topic the router writes the reply
itself; activity intents leave reply="" (the activity node speaks in Plan 2,
a stub speaks in this plan).

Resilience: the LLM is the primary classifier, but it can 401/time-out/rate-limit.
Because this is a pilgrim-SAFETY product, an LLM outage must NOT silently drop
every turn to a bare "🙏". When the LLM fails we fall back to a deterministic
trilingual keyword router so the safety-critical intents (weather, helpline,
drills/SOS, registration) still reach their activity node, and a truly generic
turn gets a helpful menu instead of an empty reply.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from agent.state import YatraState
from agent.llm import get_main_llm
from agent.i18n import LANG_NAME

VALID_INTENTS = {
    "browse", "weather", "advisory", "logistics", "helpline",
    "drills_sos", "signage", "registration", "lost_found", "grievance", "answer", "off_topic",
}

# Deterministic keyword fallback for when the LLM classifier is unavailable.
# Ordered by priority: the FIRST intent whose keywords match wins, so
# safety-critical intents are checked before broader ones. Keywords are
# trilingual (English / Marathi / Hindi). Signage deliberately does NOT match a
# bare "route" (that word also appears in "weather on the route").
_KEYWORD_INTENTS: list[tuple[str, tuple[str, ...]]] = [
    ("drills_sos", ("sos", "emergency", "help me", "drill", "first aid", "आपत्कालीन",
                    "आणीबाणी", "सराव", "प्रथमोपचार", "आपातकाल", "प्राथमिक उपचार")),
    ("helpline", ("helpline", "help line", "phone", "number", "call", "contact", "police",
                  "ambulance", "control room", "हेल्पलाइन", "फोन", "नंबर", "संपर्क", "पोलिस",
                  "पोलीस", "रुग्णवाहिका", "नियंत्रण कक्ष", "एम्बुलेंस", "पुलिस")),
    ("registration", ("register", "registration", "yatra pass", "qr", "permit", "नोंदणी",
                      "नोंदणीकृत", "पंजीकरण", "पास", "परमिट")),
    ("grievance", ("complaint", "grievance", "overcharg", "over charge", "dirty", "unclean",
                   "misbehav", "तक्रार", "गैरवर्तन", "शिकायत", "जास्त पैसे")),
    ("lost_found", ("lost", "found", "missing item", "misplaced", "lost and found", "हरवले",
                    "हरवली", "हरवला", "गहाळ", "खोया", "गुम", "खो गया")),
    ("logistics", ("pony", "palkhi", "palanquin", "porter", "transport", "bus", "fare", "rate",
                   "booking", "dindi", "पालखी", "दिंडी", "घोडा", "भाडे", "वाहतूक", "बस",
                   "पालकी", "किराया")),
    ("advisory", ("advisory", "closure", "closed", "diversion", "schedule", "notice",
                  "सूचना", "बंद", "वळण", "मार्ग बदल", "सलाह", "अलर्ट")),
    ("signage", ("map", "route map", "direction", "navigate", "which way", "signage", "नकाशा",
                 "दिशा", "मार्गदर्शन", "रास्ता दिखाओ", "नक्शा")),
    ("weather", ("weather", "rain", "forecast", "temperature", "हवामान", "पाऊस", "पाउस",
                 "तापमान", "मौसम", "बारिश", "बरसात")),
]

# Generic, never-empty fallback when the LLM is down and no keyword matched.
_FALLBACK_MENU = {
    "en": "🙏 I can help with **weather**, the **route**, **transport**, **helplines**, "
          "**safety**, **lost & found**, **grievances**, or **registration**. What do you need?",
    "mr": "🙏 मी **हवामान**, **मार्ग**, **वाहतूक**, **हेल्पलाइन**, **सुरक्षा**, "
          "**हरवले-सापडले**, **तक्रारी** किंवा **नोंदणी** याबाबत मदत करू शकतो. तुम्हाला काय हवे आहे?",
    "hi": "🙏 मैं **मौसम**, **मार्ग**, **परिवहन**, **हेल्पलाइन**, **सुरक्षा**, "
          "**खोया-पाया**, **शिकायत** या **पंजीकरण** में मदद कर सकता हूँ। आपको क्या चाहिए?",
}


def _last_user_text(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


def _keyword_intent(text: str) -> str | None:
    """First activity intent whose trilingual keywords appear in `text`, else None."""
    low = (text or "").lower()
    for intent, kws in _KEYWORD_INTENTS:
        if any(kw in low for kw in kws):
            return intent
    return None


class RouteDecision(BaseModel):
    reply: str = Field(default="", description="Reply text ONLY for answer/off_topic. Empty for activity intents.")
    intent: str = Field(description="One of: weather advisory logistics helpline drills_sos signage registration lost_found grievance answer off_topic browse")


def _system(lang: str, yatra: str) -> str:
    yatra_name = {"pandharpur": "Pandharpur Wari", "kumbh": "Simhastha Kumbh (Nashik)"}[yatra]
    return f"""You route each turn of Maharashtra Yatra Sahayak. The user is on the {yatra_name}. Reply language: {LANG_NAME[lang]} (mirror the user's script).

Pick ONE intent for the latest user turn:
- weather        — weather / rain / heat / forecast on the route or a halt
- advisory       — road closures, diversions, schedule, official advisories
- logistics      — pony / transport / palkhi / porter rates or booking; overcharge complaints
- helpline       — asking for phone numbers / who to call / police / ambulance / control room
- drills_sos     — safety preparedness, drills, first-aid, OR an emergency / SOS
- signage        — directions, route map, which way, signage, turn-by-turn
- registration   — register for the yatra, yatra pass, QR pass, group/Dindi registration
- lost_found     — lost & found: a lost belonging/item, a lost-and-found desk, reuniting with a group member (NOT a live emergency — a person missing right now is drills_sos)
- grievance      — a complaint: overcharging, bad/absent facilities, cleanliness, staff conduct, wanting to file/lodge a grievance
- answer         — a general on-topic question you can answer in 40-80 words
- off_topic      — unrelated to the yatra; politely redirect in {LANG_NAME[lang]}
- browse         — a bare greeting / "what can you do" / "menu"

For weather/advisory/logistics/helpline/drills_sos/signage/registration/lost_found/grievance set reply="" (the app responds).
For answer/off_topic/browse write `reply` in {LANG_NAME[lang]}."""


async def intent_router(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    # Deterministic SOS fast-path.
    if state.get("sos"):
        return {**state, "current_node": "intent_router", "intent": "drills_sos"}  # type: ignore[typeddict-item]

    # Sticky: stay in a registration intake until it completes.
    if state.get("reg_stage") and state.get("reg_stage") != "done":
        return {**state, "current_node": "intent_router", "intent": "registration"}  # type: ignore[typeddict-item]

    try:
        result = await get_main_llm().with_structured_output(RouteDecision).ainvoke([
            SystemMessage(content=_system(lang, yatra)),
            *messages[-6:],
        ])
        intent = result.intent if result.intent in VALID_INTENTS else "answer"
        reply = result.reply or ""
    except Exception as e:
        print(f"[intent_router] LLM failed, using keyword fallback: {e}", flush=True)
        # Deterministic fallback: keep safety-critical intents routing when the
        # LLM is unavailable, and never emit an empty reply.
        intent = _keyword_intent(_last_user_text(messages))
        if intent:
            reply = ""
        else:
            intent, reply = "answer", _FALLBACK_MENU.get(lang, _FALLBACK_MENU["en"])

    # Activity intents are answered downstream; suppress router reply.
    if intent in {"weather", "advisory", "logistics", "helpline", "drills_sos", "signage", "registration", "lost_found", "grievance"}:
        reply = ""

    updates: YatraState = {**state, "current_node": "intent_router", "intent": intent}  # type: ignore[typeddict-item]
    if reply:
        updates["messages"] = messages + [AIMessage(content=reply)]
    return updates
