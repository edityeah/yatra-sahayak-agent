"""langar activity — free-food / annachhatra / bhandara directory along each
route. Lists the camps, and if the pilgrim has shared a live location this turn,
puts the NEAREST one first with its distance."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t
from agent import persistence

_HEADER = {
    "mr": "🍲 **मोफत अन्नदान / लंगर**",
    "hi": "🍲 **मुफ्त अन्नदान / लंगर**",
    "en": "🍲 **Free food / langar (annadan)**",
}
_NEAREST = {
    "mr": "📍 सर्वात जवळचे ({km} किमी):",
    "hi": "📍 सबसे नज़दीकी ({km} किमी):",
    "en": "📍 Nearest to you ({km} km):",
}
_EMPTY = {
    "mr": "या यात्रेसाठी अन्नदान माहिती लवकरच जोडली जाईल.",
    "hi": "इस यात्रा के लिए अन्नदान जानकारी शीघ्र जोड़ी जाएगी।",
    "en": "Free-food details for this yatra will be added soon.",
}


def _one(e: dict, lang: str) -> str:
    line = f"**{t(e['name'], lang)}** — {t(e.get('location'), lang)}"
    if e.get("note"):
        line += f"\n  {t(e['note'], lang)}"
    return line


async def langar(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    entries = load("langar").get(yatra, [])
    if not entries:
        body = _EMPTY[lang]
    else:
        lines = [_HEADER[lang], ""]
        loc = state.get("shared_location") or {}
        lat, lng = loc.get("lat"), loc.get("lng")
        if lat is not None and lng is not None:
            withd = [(persistence._haversine_km(lat, lng, e["lat"], e["lng"]), e)
                     for e in entries if e.get("lat") is not None]
            if withd:
                d, nearest = min(withd, key=lambda x: x[0])
                lines.append(_NEAREST[lang].format(km=round(d, 1)))
                lines.append(_one(nearest, lang))
                lines.append("")
        for e in entries:
            lines.append(_one(e, lang))
        body = "\n".join(lines).rstrip()

    return {
        **state,
        "current_node": "langar",
        "messages": messages + [AIMessage(content=body)],
    }
