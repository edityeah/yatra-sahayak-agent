"""grievance activity — points a pilgrim to the Grievance module to file a
complaint (overcharging, facilities, cleanliness, safety, staff conduct). The
report lands in the officer war-room's grievance dashboard.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.config import get_settings

_BODY = {
    "mr": ("📝 **तक्रार नोंदवा**\n\n"
           "जास्त दर, सुविधा, स्वच्छता, सुरक्षा किंवा कर्मचाऱ्यांबद्दल तक्रार नोंदवा — "
           "ती थेट नियंत्रण कक्षाकडे जाते.\n\n[📝 तक्रार नोंदवा]({url})\n\n"
           "आणीबाणी असल्यास **112** वर कॉल करा."),
    "hi": ("📝 **शिकायत दर्ज करें**\n\n"
           "अधिक दाम, सुविधा, स्वच्छता, सुरक्षा या कर्मचारियों के बारे में शिकायत दर्ज करें — "
           "यह सीधे नियंत्रण कक्ष तक जाती है।\n\n[📝 शिकायत दर्ज करें]({url})\n\n"
           "आपात स्थिति में **112** पर कॉल करें।"),
    "en": ("📝 **File a grievance**\n\n"
           "Report overcharging, facilities, cleanliness, safety, or staff conduct — "
           "it goes straight to the control room.\n\n[📝 File a grievance]({url})\n\n"
           "For an emergency, call **112**."),
}


async def grievance(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"
    url = f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/grievance?yatra={yatra}&lang={lang}"
    return {
        **state,
        "current_node": "grievance",
        "messages": messages + [AIMessage(content=_BODY[lang].format(url=url))],
    }
