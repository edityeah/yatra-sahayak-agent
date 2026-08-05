"""palkhi activity — live palkhi tracking (official Solapur/Pune police trackers),
the Wari schedule, and the statewide nodal-officer + palkhi-chief directory (all
11 palkhis). Data mirrors the Solapur Rural Police Ashadhi Wari system."""
from __future__ import annotations
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.seed import load, t
from agent.nodes.activities.followups import followup_line

_HEADER = {
    "mr": "🚩 **पालखी थेट मागोवा, वेळापत्रक व नियंत्रण अधिकारी**",
    "hi": "🚩 **पालकी लाइव ट्रैकिंग, कार्यक्रम व नोडल अधिकारी**",
    "en": "🚩 **Palkhi tracking, schedule & nodal officers**",
}
# The 11 sant palkhis start from ACROSS Maharashtra and converge on Pandharpur
# through the Pune → Satara → Solapur corridor (hence two official trackers).
_STATEWIDE = {
    "mr": "महाराष्ट्रभरातून ११ संत पालख्या पंढरपूरकडे — पुणे → सातारा → सोलापूर मार्गे.",
    "hi": "पूरे महाराष्ट्र से 11 संत पालकियाँ पंढरपुर की ओर — पुणे → सातारा → सोलापुर मार्ग से।",
    "en": "11 sant palkhis from across Maharashtra converge on Pandharpur via the Pune → Satara → Solapur corridor.",
}
_TRACK = {
    "mr": "📍 थेट पालखी मागोवा (यात्राकाळात): {url}\n(पुणे टप्पा: {pune})",
    "hi": "📍 लाइव पालकी ट्रैकिंग (यात्रा काल में): {url}\n(पुणे चरण: {pune})",
    "en": "📍 Live palkhi tracking (during the yatra): {url}\n(Pune leg: {pune})",
}
_SCHED = {"mr": "🗓️ वेळापत्रक", "hi": "🗓️ कार्यक्रम", "en": "🗓️ Schedule"}
_DIR = {"mr": "👥 सर्व ११ पालख्या — प्रमुख व नियंत्रण अधिकारी (संपूर्ण महाराष्ट्र)",
        "hi": "👥 सभी 11 पालकियाँ — प्रमुख व नोडल अधिकारी (संपूर्ण महाराष्ट्र)",
        "en": "👥 All 11 palkhis — chiefs & nodal officers (across Maharashtra)"}
_CHIEF = {"mr": "प्रमुख", "hi": "प्रमुख", "en": "Chief"}
_NODAL = {"mr": "नियंत्रण अधिकारी", "hi": "नोडल अधिकारी", "en": "Nodal"}

# Officer directory is PII-ish but published by the police for pilgrims. Show
# the full directory only when the user asks for officer contacts; for a plain
# "track the palkhi" query, keep it to the tracker + schedule.
_NODAL_WORDS = ("nodal", "officer", "chief", "contact", "number", "phone",
                "अधिकारी", "नियंत्रण", "प्रमुख", "संपर्क", "क्रमांक", "नंबर")


def _last_human(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content).lower()
    return ""


async def palkhi(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    data = load("palkhis")
    meta = data.get("meta", {})
    sched = meta.get("schedule", {})

    lines = [_HEADER[lang], "", _STATEWIDE[lang], ""]
    lines.append(_TRACK[lang].format(url=meta.get("tracker_url", ""),
                                     pune=meta.get("pune_tracker_url", "")))
    lines.append("")
    lines.append(f"**{_SCHED[lang]}**")
    for key in ("period", "main_days", "entries"):
        if sched.get(key):
            lines.append(f"- {t(sched[key], lang)}")

    if any(w in _last_human(messages) for w in _NODAL_WORDS):
        lines.append("")
        lines.append(f"**{_DIR[lang]}**")
        for p in data.get("palkhis", []):
            lines.append(f"**{p['name']}** — {p.get('origin','')}")
            if p.get("chief_phone"):
                lines.append(f"  {_CHIEF[lang]}: {p.get('chief','')} "
                             f"[{p['chief_phone']}](tel:{p['chief_phone']})")
            if p.get("nodal_phone"):
                lines.append(f"  {_NODAL[lang]}: {p.get('nodal','')}, {p.get('nodal_ps','')} "
                             f"[{p['nodal_phone']}](tel:{p['nodal_phone']})")

    body = "\n".join(lines).rstrip() + followup_line("palkhi", lang)
    return {**state, "current_node": "palkhi",
            "messages": messages + [AIMessage(content=body)]}
