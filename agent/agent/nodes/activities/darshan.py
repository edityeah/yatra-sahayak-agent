"""darshan activity — temple darshan / aarti timings and (for Kumbh) shahi-snan
info, so the agent can answer the core pilgrimage question directly."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t
from agent.nodes.activities.followups import followup_line

_EMPTY = {
    "mr": "दर्शन माहिती लवकरच जोडली जाईल.",
    "hi": "दर्शन जानकारी शीघ्र जोड़ी जाएगी।",
    "en": "Darshan details will be added soon.",
}


async def darshan(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    data = load("darshan").get(yatra)
    if not data:
        body = _EMPTY[lang]
    else:
        lines = [t(data.get("title"), lang), ""]
        for item in data.get("items", []):
            lines.append(f"**{t(item.get('label'), lang)}** — {t(item.get('value'), lang)}")
        body = "\n".join(lines).rstrip() + followup_line("darshan", lang)

    return {
        **state,
        "current_node": "darshan",
        "messages": messages + [AIMessage(content=body)],
    }
