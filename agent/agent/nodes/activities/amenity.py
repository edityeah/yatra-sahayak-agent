"""amenity activity — 'nearest medical post / toilet / drinking water / bathing
ghat' from the route facility map. Uses the same nearest-by-distance engine as
SOS routing: with a shared live location it names the closest one first."""
from __future__ import annotations
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.seed import load, t
from agent import persistence
from agent.nodes.activities.followups import followup_line

# Facility kind (matches routes.json `kind`) → trilingual label + detection words.
_KINDS = [
    ("medical", {"mr": "आरोग्य केंद्र", "hi": "स्वास्थ्य केंद्र", "en": "Medical post"},
     ("medical", "hospital", "doctor", "first aid", "ambulance", "clinic", "sick", "injur",
      "आरोग्य", "दवाखाना", "रुग्ण", "वैद्यकीय", "अस्पताल", "चिकित्सा", "डॉक्टर")),
    ("water", {"mr": "पिण्याचे पाणी", "hi": "पेयजल", "en": "Drinking water"},
     ("water", "drinking", "thirsty", "पाणी", "पानी", "पेयजल")),
    ("toilet", {"mr": "शौचालय", "hi": "शौचालय", "en": "Toilet"},
     ("toilet", "washroom", "restroom", "शौचालय", "टॉयलेट", "स्वच्छता")),
    ("ghat", {"mr": "घाट / स्नान", "hi": "घाट / स्नान", "en": "Bathing ghat"},
     ("ghat", "bath", "snan", "river", "घाट", "स्नान", "नदी")),
]
_HEADER = {
    "mr": "📍 **जवळच्या सुविधा — {kind}**",
    "hi": "📍 **नज़दीकी सुविधाएँ — {kind}**",
    "en": "📍 **Nearby facilities — {kind}**",
}
_NEAREST = {
    "mr": "सर्वात जवळचे ({km} किमी): **{name}**",
    "hi": "सबसे नज़दीकी ({km} किमी): **{name}**",
    "en": "Nearest ({km} km): **{name}**",
}
_ASK_LOC = {
    "mr": "\n💡 अचूक 'सर्वात जवळचे' साठी तुमचे लोकेशन शेअर करा (📎 → Location).",
    "hi": "\n💡 सटीक 'सबसे नज़दीकी' के लिए अपना लोकेशन शेयर करें (📎 → Location)।",
    "en": "\n💡 Share your location (📎 → Location) for an exact 'nearest' result.",
}
_EMPTY = {
    "mr": "या प्रकारची सुविधा नकाशावर सध्या नोंदलेली नाही.",
    "hi": "इस प्रकार की सुविधा मानचित्र पर अभी दर्ज नहीं है।",
    "en": "No facility of this kind is mapped for this route yet.",
}


def _last_human(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content).lower()
    return ""


_LABELS = {k: label for k, label, _ in _KINDS}


def _detect_kind(text: str) -> tuple[str, dict]:
    for kind, label, words in _KINDS:
        if any(w in text for w in words):
            return kind, label
    return _KINDS[0][0], _KINDS[0][1]   # default → medical (most safety-relevant)


async def amenity(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    # The kind may come from a sticky "amenity:<kind>" flag (the follow-up
    # location turn has no keyword) or be detected from the message.
    aw = state.get("awaiting") or ""
    if aw.startswith("amenity:") and aw.split(":", 1)[1] in _LABELS:
        kind = aw.split(":", 1)[1]
        label = _LABELS[kind]
    else:
        kind, label = _detect_kind(_last_human(messages))

    pois = [p for p in load("routes").get(yatra, []) if p.get("kind") == kind]
    awaiting = None

    if not pois:
        body = _EMPTY[lang]
    else:
        lines = [_HEADER[lang].format(kind=t(label, lang)), ""]
        loc = state.get("shared_location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is not None and lng is not None:
            withd = [(persistence._haversine_km(lat, lng, p["lat"], p["lng"]), p)
                     for p in pois if p.get("lat") is not None]
            if withd:
                d, near = min(withd, key=lambda x: x[0])
                lines.append(_NEAREST[lang].format(km=round(d, 1), name=t(near["name"], lang)))
                if near.get("note"):
                    lines.append(t(near["note"], lang))
                lines.append("")
        for p in pois:
            line = f"- {t(p['name'], lang)}"
            if p.get("note"):
                line += f" — {t(p['note'], lang)}"
            lines.append(line)
        if lat is None:
            lines.append(_ASK_LOC[lang])
            awaiting = f"amenity:{kind}"   # so the next shared pin re-routes here
        body = "\n".join(lines).rstrip() + followup_line("amenity", lang)

    return {
        **state,
        "current_node": "amenity",
        "awaiting": awaiting,   # type: ignore[typeddict-item]
        "messages": messages + [AIMessage(content=body)],
    }
