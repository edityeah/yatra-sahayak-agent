"""parking activity — GPS-navigable parking lots for the yatra town, each with a
Google Maps link (mirrors the Solapur Police Wari parking directory)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import load, t
from agent.nodes.activities.followups import followup_line

_HEADER = {
    "mr": "🅿️ **वाहनतळ (GPS मार्गदर्शनासह)**",
    "hi": "🅿️ **पार्किंग (GPS नेविगेशन सहित)**",
    "en": "🅿️ **Parking (GPS-navigable)**",
}
_OUTER = {"mr": "बाहेरील वाहनतळ", "hi": "बाहरी पार्किंग", "en": "Outer parking"}
_INNER = {"mr": "आतील वाहनतळ", "hi": "भीतरी पार्किंग", "en": "Inner parking"}
_NAV = {"mr": "मार्ग", "hi": "रास्ता", "en": "Navigate"}
_EMPTY = {
    "mr": "या यात्रेसाठी वाहनतळ माहिती लवकरच जोडली जाईल.",
    "hi": "इस यात्रा के लिए पार्किंग जानकारी शीघ्र जोड़ी जाएगी।",
    "en": "Parking details for this yatra will be added soon.",
}


async def parking(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    lots = load("parking").get(yatra, [])
    if not lots:
        body = _EMPTY[lang]
    else:
        lines = [_HEADER[lang], ""]
        for zone, label in (("outer", _OUTER), ("inner", _INNER)):
            zlots = [l for l in lots if l.get("zone") == zone]
            if not zlots:
                continue
            lines.append(f"**{label[lang]}**")
            for l in zlots:
                lines.append(f"- {l['name']} — [{_NAV[lang]}]({l['maps_url']})")
            lines.append("")
        body = "\n".join(lines).rstrip() + followup_line("parking", lang)

    return {**state, "current_node": "parking",
            "messages": messages + [AIMessage(content=body)]}
