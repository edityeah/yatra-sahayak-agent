"""drills_sos activity — live SOS event creation + calm ack, and preparedness
drills listing (Plan 2 Task 9).

Deterministic, no LLM: this node is safety-critical and must behave
predictably under emergency conditions.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent import persistence
from agent.seed import load, t

# ── SOS: keyword → deterministic `nature` label ─────────────────────
_NATURE_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("stampede", "crowd crush", "crowd"), "stampede/crowd"),
    (("medical", "heart", "unconscious", "faint", "breathless", "breathing"), "medical"),
    (("drown", "drowning", "water"), "drowning/water"),
    (("fire", "burn", "smoke"), "fire"),
    (("missing", "lost", "separated"), "missing person"),
]


def _infer_nature(text: str) -> str:
    lowered = text.lower()
    for keywords, label in _NATURE_KEYWORDS:
        if any(k in lowered for k in keywords):
            return label
    return "unspecified"


_SOS_ACK = {
    "mr": "🆘 आपली आपत्कालीन सूचना नियंत्रण कक्षाला पाठवली आहे{control}. जर तुम्ही तात्काळ धोक्यात असाल तर आत्ताच **112** वर कॉल करा. कृपया जिथे आहात तिथेच थांबा व शांत राहा — मदत येत आहे.",
    "hi": "🆘 आपकी आपातकालीन सूचना नियंत्रण कक्ष को भेज दी गई है{control}। यदि आप तुरंत खतरे में हैं तो अभी **112** पर कॉल करें। कृपया जहाँ हैं वहीं रुकें और शांत रहें — मदद आ रही है।",
    "en": "🆘 Your emergency alert has been sent to the control room{control}. If you are in immediate danger, call **112** right now. Please stay where you are and stay calm — help is on the way.",
}

_SOS_CONTROL_SUFFIX = {
    "mr": " (नियंत्रण कक्ष: {number})",
    "hi": " (नियंत्रण कक्ष: {number})",
    "en": " (control room: {number})",
}

# Compact trilingual ack used when the language is not yet known (e.g. SOS
# fires on the very first turn, before language selection) — an emergency
# must never be blocked on a menu choice.
_SOS_ACK_TRILINGUAL_COMPACT = {
    "mr": "🆘 नियंत्रण कक्षाला कळवले आहे{control}. धोका असल्यास आत्ताच **112** वर कॉल करा. जिथे आहात तिथेच थांबा.",
    "hi": "🆘 नियंत्रण कक्ष को सूचित कर दिया गया है{control}। खतरा हो तो अभी **112** पर कॉल करें। जहाँ हैं वहीं रुकें।",
    "en": "🆘 The control room has been alerted{control}. If in danger, call **112** now. Stay where you are.",
}

_DRILLS_HEADER = {
    "mr": "🦺 **सुरक्षा तयारी माहिती** / Preparedness drills",
    "hi": "🦺 **सुरक्षा तैयारी जानकारी** / Preparedness drills",
    "en": "🦺 **Preparedness drills / safety information**",
}

# Appended to the SOS ack when we do NOT yet have coordinates — asks the pilgrim
# to share their live location so responders route to the NEAREST police control.
_SOS_ASK_LOCATION = {
    "mr": "\n\n📍 कृपया तुमचे **थेट लोकेशन शेअर करा** (📎 → Location) — म्हणजे जवळचे पोलीस नियंत्रण तुमच्यापर्यंत लवकर पोहोचेल.",
    "hi": "\n\n📍 कृपया अपना **लाइव लोकेशन शेयर करें** (📎 → Location) — ताकि नज़दीकी पुलिस नियंत्रण आप तक जल्दी पहुँचे।",
    "en": "\n\n📍 Please **share your live location** (📎 → Location) so the nearest police control can reach you faster.",
}
# Appended when we already have coordinates — names the nearest control.
_SOS_NEAREST = {
    "mr": "\n\n📍 सर्वात जवळचे मदत केंद्र: **{control}**. मदत तुमच्याकडे पाठवली जात आहे.",
    "hi": "\n\n📍 सबसे नज़दीकी मदद केंद्र: **{control}**। मदद आपकी ओर भेजी जा रही है।",
    "en": "\n\n📍 Nearest help: **{control}**. Responders are being directed to you.",
}
# The confirmation after a live pin arrives for an open SOS.
_SOS_LOCATED = {
    "mr": "✅ तुमचे लोकेशन मिळाले. सर्वात जवळचे मदत केंद्र — **{control}** — यांना कळवले आहे. जिथे आहात तिथेच थांबा.",
    "hi": "✅ आपका लोकेशन मिल गया। सबसे नज़दीकी मदद केंद्र — **{control}** — को सूचित कर दिया गया है। जहाँ हैं वहीं रुकें।",
    "en": "✅ Got your location. The nearest help — **{control}** — has been notified. Stay where you are.",
}


def _control_room_number(sos_yatra: str | None) -> str | None:
    if not sos_yatra:
        return None
    yatras = load("yatras")
    entry = yatras.get(sos_yatra)
    return entry.get("control_room") if entry else None


def _last_human_text(messages: list) -> str:
    for msg in reversed(messages or []):
        content = getattr(msg, "content", None)
        msg_type = getattr(msg, "type", None)
        if content and msg_type in (None, "human"):
            return str(content)
    return ""


async def _handle_sos(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    user_id = state.get("user_id")
    lang = state.get("language")

    reg = await persistence.get_registration_for_user(user_id)
    sos_yatra = state.get("active_yatra") or (reg["yatra"] if reg else None)
    yatra_id = reg["yatra_id"] if reg else None

    nature = _infer_nature(_last_human_text(messages))

    # Capture the pilgrim's location if they've shared a live pin this turn — it
    # routes the SOS to the NEAREST police control. If not, we still raise the
    # SOS immediately (safety first) and ask for a pin as a follow-up.
    loc = state.get("shared_location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")

    await persistence.create_sos(
        user_id, yatra=sos_yatra, yatra_id=yatra_id, location=None, nature=nature,
        lat=lat, lng=lng,
        reporter_name=(reg["name"] if reg else None),
        reporter_phone=(reg["phone"] if reg else None),
    )

    control_number = _control_room_number(sos_yatra)

    if lang:
        control_str = _SOS_CONTROL_SUFFIX[lang].format(number=control_number) if control_number else ""
        body = _SOS_ACK[lang].format(control=control_str)
    else:
        lines = []
        for code in ("mr", "hi", "en"):
            control_str = _SOS_CONTROL_SUFFIX[code].format(number=control_number) if control_number else ""
            lines.append(_SOS_ACK_TRILINGUAL_COMPACT[code].format(control=control_str))
        body = "\n".join(lines)

    # With coordinates: name the nearest control, no follow-up needed. Without:
    # ask for a live pin and stay sticky so the next location message re-routes.
    awaiting = None
    if lat is not None and lng is not None:
        nearest = persistence.sos_control_for(sos_yatra, lat, lng)
        body += _SOS_NEAREST.get(lang or "en", _SOS_NEAREST["en"]).format(control=nearest)
    else:
        awaiting = "sos_location"
        body += _SOS_ASK_LOCATION.get(lang or "en", _SOS_ASK_LOCATION["en"])

    return {
        **state,
        "current_node": "drills_sos",
        "awaiting": awaiting,   # type: ignore[typeddict-item]
        "messages": messages + [AIMessage(content=body)],
    }


async def _handle_sos_locate(state: YatraState) -> YatraState:
    """A live pin arrived for an open SOS — attach it and re-route to the
    nearest police control."""
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    user_id = state.get("user_id")
    loc = state.get("shared_location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")

    sos = await persistence.update_latest_open_sos_location(user_id, lat, lng)
    control = sos["routed_to"] if sos else persistence.sos_control_for(
        state.get("active_yatra"), lat, lng)
    body = _SOS_LOCATED.get(lang, _SOS_LOCATED["en"]).format(control=control)

    return {
        **state,
        "current_node": "drills_sos",
        "awaiting": None,          # type: ignore[typeddict-item]
        "sos_locate": False,       # type: ignore[typeddict-item]
        "shared_location": None,   # type: ignore[typeddict-item]
        "messages": messages + [AIMessage(content=body)],
    }


async def _handle_drills(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"

    modules = load("drills")
    lines = [_DRILLS_HEADER[lang], ""]
    for module in modules:
        lines.append(f"**{t(module['title'], lang)}** — {t(module['body'], lang)}")
        lines.append("")

    return {
        **state,
        "current_node": "drills_sos",
        "messages": messages + [AIMessage(content="\n".join(lines).rstrip())],
    }


async def drills_sos(state: YatraState) -> YatraState:
    if state.get("sos_locate"):
        return await _handle_sos_locate(state)
    if state.get("sos"):
        return await _handle_sos(state)
    return await _handle_drills(state)
