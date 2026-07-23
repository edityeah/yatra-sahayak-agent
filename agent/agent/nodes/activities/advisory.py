"""advisory activity — seed-backed district advisories, sorted by severity (Plan 2 Task 7)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t

_HEADER = {
    "mr": "📢 **जिल्हा प्रशासन सूचना**",
    "hi": "📢 **जिला प्रशासन सूचनाएँ**",
    "en": "📢 **District administration advisories**",
}

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


async def advisory(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    entries = load("advisories").get(yatra, [])
    ordered = sorted(entries, key=lambda e: _SEVERITY_ORDER.get(e.get("severity", "info"), 99))

    lines = [_HEADER[lang], ""]
    for entry in ordered:
        severity = str(entry.get("severity", "info")).upper()
        lines.append(f"**[{severity}]** {t(entry['title'], lang)}")
        lines.append(t(entry["body"], lang))
        lines.append("")

    return {
        **state,
        "current_node": "advisory",
        "messages": messages + [AIMessage(content="\n".join(lines).rstrip())],
    }
