"""logistics activity — seed-backed notified-rate table (Plan 2 Task 6)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t

_HEADER = {
    "mr": "🐎 **सूचक शासकीय दरपत्रक** (हे अंदाजे, प्रशासनाने सुचवलेले दर आहेत)",
    "hi": "🐎 **सांकेतिक सरकारी दर सूची** (ये प्रशासन द्वारा सुझाए गए अनुमानित दर हैं)",
    "en": "🐎 **Indicative government-notified rates** (approximate — set by the district administration)",
}

_OVERCHARGE_LINE = {
    "mr": "⚠️ जास्त पैसे मागितले? नियंत्रण कक्षाला कळवा.",
    "hi": "⚠️ ज़्यादा पैसे माँगे गए? नियंत्रण कक्ष को सूचित करें।",
    "en": "⚠️ Being overcharged? Report it via the control room.",
}


async def logistics(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    entries = load("logistics_rates").get(yatra, [])
    lines = [_HEADER[lang], ""]
    for entry in entries:
        line = f"- {t(entry['service'], lang)}: {t(entry['rate'], lang)} / {t(entry['unit'], lang)}"
        if entry.get("note"):
            line += f" — {t(entry['note'], lang)}"
        lines.append(line)

    lines.append("")
    lines.append(_OVERCHARGE_LINE[lang])

    return {
        **state,
        "current_node": "logistics",
        "messages": messages + [AIMessage(content="\n".join(lines))],
    }
