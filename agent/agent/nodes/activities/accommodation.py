"""accommodation activity — seed-backed camp / Bhakta Niwas / tent tariffs, so
the agent can answer "where can I stay tonight and what does it cost"."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t

_HEADER = {
    "mr": "🏠 **निवास व्यवस्था व दर**",
    "hi": "🏠 **आवास व्यवस्था व दर**",
    "en": "🏠 **Accommodation & tariffs**",
}
_EMPTY = {
    "mr": "या यात्रेसाठी निवास माहिती लवकरच जोडली जाईल.",
    "hi": "इस यात्रा के लिए आवास जानकारी शीघ्र जोड़ी जाएगी।",
    "en": "Accommodation details for this yatra will be added soon.",
}
_CONTACT = {"mr": "संपर्क", "hi": "संपर्क", "en": "Contact"}


async def accommodation(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    entries = load("accommodation").get(yatra, [])
    if not entries:
        body = _EMPTY[lang]
    else:
        lines = [_HEADER[lang], ""]
        for e in entries:
            lines.append(f"**{t(e['name'], lang)}** — {t(e.get('type'), lang)}")
            lines.append(f"₹ {e.get('tariff', '')}")
            if e.get("note"):
                lines.append(t(e["note"], lang))
            if e.get("contact"):
                lines.append(f"{_CONTACT[lang]}: {e['contact']}")
            lines.append("")
        body = "\n".join(lines).rstrip()

    return {
        **state,
        "current_node": "accommodation",
        "messages": messages + [AIMessage(content=body)],
    }
