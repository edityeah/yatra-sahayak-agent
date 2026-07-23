"""helpline activity — seed-backed emergency/control-room dialling list (Plan 2 Task 5)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t

_HEADER = {
    "mr": "☎️ **आपत्कालीन क्रमांक व मदत कक्ष**",
    "hi": "☎️ **आपातकालीन नंबर व सहायता केंद्र**",
    "en": "☎️ **Emergency numbers & helplines**",
}


async def helpline(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    entries = load("helplines").get(yatra, [])
    lines = [_HEADER[lang], ""]
    for entry in entries:
        lines.append(f"- {t(entry['label'], lang)}: [{entry['number']}](tel:{entry['dial']})")

    return {
        **state,
        "current_node": "helpline",
        "messages": messages + [AIMessage(content="\n".join(lines))],
    }
