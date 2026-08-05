"""signage activity — seed-backed turn-by-turn guidance + route-map link (Plan 2 Task 8)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t
from agent.config import get_settings

_HEADER = {
    "mr": "🧭 **मार्ग खुणा व दिशादर्शक सूचना**",
    "hi": "🧭 **मार्ग चिह्न व दिशा-निर्देश**",
    "en": "🧭 **Route signage & directions**",
}

_MAP_LINE = {
    "mr": "पूर्ण मार्ग नकाशा येथे पहा",
    "hi": "पूरा मार्ग मानचित्र यहाँ देखें",
    "en": "View the full route map",
}
_BUS_HEADER = {
    "mr": "🚌 एसटी बस मार्ग (विभागनिहाय)",
    "hi": "🚌 एसटी बस मार्ग (क्षेत्रवार)",
    "en": "🚌 ST bus routes (by region)",
}


async def signage(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    entries = load("signage").get(yatra, [])
    lines = [_HEADER[lang], ""]
    for entry in entries:
        lines.append(f"- {t(entry['at'], lang)}: {t(entry['guidance'], lang)}")

    # Bus-route guide (folded in here per the route activity).
    bus = load("bus_routes").get(yatra, [])
    if bus:
        lines.append("")
        lines.append(f"**{_BUS_HEADER[lang]}**")
        for b in bus:
            lines.append(f"- {t(b['region'], lang)}")

    map_url = f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/map?yatra={yatra}"
    lines.append("")
    lines.append(f"[{_MAP_LINE[lang]}]({map_url})")

    return {
        **state,
        "current_node": "signage",
        "messages": messages + [AIMessage(content="\n".join(lines))],
    }
