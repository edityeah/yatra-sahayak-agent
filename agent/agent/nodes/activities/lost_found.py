"""lost_found activity — points the yatri to the Lost & Found module (report a
missing person / lost belonging, or browse the board) and reinforces the
emergency path. A genuinely missing *person right now* trips the SOS keyword
gate upstream and is fast-pathed to drills_sos instead; this node handles the
calmer "lost bag / lost & found desk" ask.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.config import get_settings

_BODY = {
    "mr": ("🧿 **हरवले–सापडले**\n\n"
           "हरवलेली व्यक्ती किंवा वस्तू नोंदवा, किंवा सापडलेली वस्तू कळवा — "
           "आणि नोंदींची यादी पाहा.\n\n[🧿 हरवले–सापडले उघडा]({url})\n\n"
           "⚠️ एखादी व्यक्ती किंवा लहान मूल आत्ता हरवले असल्यास लगेच **112** वर "
           "कॉल करा आणि मला सांगा — मी तातडीने SOS नोंदवतो."),
    "hi": ("🧿 **खोया–पाया**\n\n"
           "खोई हुई व्यक्ति या वस्तु दर्ज करें, या मिली हुई वस्तु बताएं — "
           "और सूची देखें।\n\n[🧿 खोया–पाया खोलें]({url})\n\n"
           "⚠️ कोई व्यक्ति या बच्चा अभी खो गया हो तो तुरंत **112** पर कॉल करें और "
           "मुझे बताएं — मैं तुरंत SOS दर्ज करता हूँ।"),
    "en": ("🧿 **Lost & Found**\n\n"
           "Report a missing person or a lost belonging, report something you've "
           "found, or check the board.\n\n[🧿 Open Lost & Found]({url})\n\n"
           "⚠️ If a person or child is missing right now, call **112** immediately "
           "and tell me — I'll raise an SOS at once."),
}


async def lost_found(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"
    url = f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/lostfound?yatra={yatra}&lang={lang}"
    return {
        **state,
        "current_node": "lost_found",
        "messages": messages + [AIMessage(content=_BODY[lang].format(url=url))],
    }
