"""registration activity — multi-turn simulated-eKYC intake → QR yatra pass.

Simulated e-KYC ONLY: we collect name + phone as a mock Aadhaar-style KYC.
We NEVER ask for or store a real Aadhaar number. The active stage + collected
fields persist across turns via the webhook (user_state). On completion a
Yatra ID is issued and a pass link (rendered as a QR in the Plan 3 web app)
is returned.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.config import get_settings
from agent import persistence

# Ordered intake stages after the (implicit) start.
_NEXT = {"name": "phone", "phone": "group", "group": "emergency",
         "emergency": "medical", "medical": "confirm"}

# Stages that mean "an intake is in progress". Anything else (None, "done",
# a cancelled/unknown value) means we should start a fresh registration.
_IN_PROGRESS_STAGES = set(_NEXT) | {"confirm"}

_PROMPTS = {
    "name": {
        "mr": "चला, यात्रेसाठी नोंदणी करूया. तुमचे **पूर्ण नाव** काय आहे? (सिम्युलेटेड e-KYC — आधार क्रमांक नको)",
        "hi": "आइए यात्रा के लिए पंजीकरण करें। आपका **पूरा नाम** क्या है? (सिम्युलेटेड e-KYC — आधार संख्या की ज़रूरत नहीं)",
        "en": "Let's register you for the yatra. What's your **full name**? (simulated e-KYC — no Aadhaar number needed)",
    },
    "phone": {"mr": "तुमचा **मोबाइल क्रमांक**?", "hi": "आपका **मोबाइल नंबर**?", "en": "Your **mobile number**?"},
    "group": {"mr": "तुम्ही कोणत्या **दिंडी/गटा**सोबत आहात? (एकटे असल्यास 'none')",
              "hi": "आप किस **दिंडी/समूह** के साथ हैं? (अकेले हों तो 'none')",
              "en": "Which **Dindi / group** are you with? (type 'none' if solo)"},
    "emergency": {"mr": "**आपत्कालीन संपर्क** क्रमांक?", "hi": "**आपातकालीन संपर्क** नंबर?", "en": "An **emergency contact** number?"},
    "medical": {"mr": "काही **वैद्यकीय बाब** नोंदवायची? (उदा. वृद्ध, हृदयविकार) नसल्यास 'none'.",
                "hi": "कोई **चिकित्सीय जानकारी**? (जैसे बुज़ुर्ग, हृदय रोग) न हो तो 'none'.",
                "en": "Any **medical flags** to note (e.g. elderly, heart condition)? Type 'none' if not."},
}

_FIELD_OF_STAGE = {"name": "name", "phone": "phone", "group": "group_name",
                   "emergency": "emergency_contact", "medical": "medical_flags"}


def _last_user(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content).strip()
    return ""


def _confirm_prompt(fields: dict, lang: str) -> str:
    summary = (f"- Name: {fields.get('name','')}\n"
               f"- Mobile: {fields.get('phone','')}\n"
               f"- Group: {fields.get('group_name','')}\n"
               f"- Emergency: {fields.get('emergency_contact','')}\n"
               f"- Medical: {fields.get('medical_flags','')}")
    head = {"mr": "कृपया तपशील तपासा आणि पास तयार करण्यासाठी **'हो'** लिहा:",
            "hi": "कृपया विवरण जाँचें और पास बनाने के लिए **'हाँ'** लिखें:",
            "en": "Please check your details and reply **'yes'** to issue your pass:"}[lang]
    return f"{head}\n\n{summary}"


def _is_yes(text: str) -> bool:
    t_ = text.strip().lower()
    return t_ in ("yes", "y", "हो", "हाँ", "haan", "ho", "confirm", "ok", "okay")


async def registration(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"
    user_id = state.get("user_id")
    stage = state.get("reg_stage")
    fields = dict(state.get("reg_fields") or {})

    def _emit(reply: str, *, reg_stage, reg_fields) -> YatraState:
        return {**state, "current_node": "registration", "reg_stage": reg_stage,
                "reg_fields": reg_fields, "messages": messages + [AIMessage(content=reply)]}

    # Start (or restart) intake — ask for the name (do not consume the
    # "register" trigger turn). A prior "done"/cancelled/unknown stage begins a
    # clean registration with empty fields (avoids re-entry KeyError + stale data).
    if stage not in _IN_PROGRESS_STAGES:
        return _emit(_PROMPTS["name"][lang], reg_stage="name", reg_fields={})

    answer = _last_user(messages)

    # Confirm stage — issue on yes, else cancel.
    if stage == "confirm":
        if _is_yes(answer):
            yatra_id = await persistence.create_registration(
                user_id, yatra=yatra, name=fields.get("name", ""), phone=fields.get("phone", ""),
                group_name=fields.get("group_name", ""), emergency_contact=fields.get("emergency_contact", ""),
                medical_flags=fields.get("medical_flags", ""))
            pass_url = f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/pass?id={yatra_id}"
            done = {"mr": f"✅ नोंदणी पूर्ण! तुमचा **यात्रा ID: {yatra_id}**.\n\n[📲 तुमचा QR यात्रा पास उघडा]({pass_url})",
                    "hi": f"✅ पंजीकरण पूरा! आपका **यात्रा ID: {yatra_id}**.\n\n[📲 अपना QR यात्रा पास खोलें]({pass_url})",
                    "en": f"✅ Registration complete! Your **Yatra ID: {yatra_id}**.\n\n[📲 Open your QR yatra pass]({pass_url})"}[lang]
            return _emit(done, reg_stage="done", reg_fields=fields)
        cancel = {"mr": "नोंदणी रद्द केली. पुन्हा सुरू करण्यासाठी 'नोंदणी' लिहा.",
                  "hi": "पंजीकरण रद्द किया गया। फिर से शुरू करने के लिए 'पंजीकरण' लिखें।",
                  "en": "Registration cancelled. Type 'register' to start again."}[lang]
        return _emit(cancel, reg_stage="done", reg_fields=fields)

    # Collecting a field: store the answer for the current stage, advance.
    field = _FIELD_OF_STAGE.get(stage)
    if field:
        fields[field] = answer
    nxt = _NEXT.get(stage)
    if nxt == "confirm":
        return _emit(_confirm_prompt(fields, lang), reg_stage="confirm", reg_fields=fields)
    return _emit(_PROMPTS[nxt][lang], reg_stage=nxt, reg_fields=fields)
