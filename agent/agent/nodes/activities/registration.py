"""registration activity — multi-turn yatra-pass intake with simulated
verification, modelled on the Char Dham Yatra registration (UTDB tourist-care
portal) and the Amarnath Yatra permit (SASB).

Flow: yatra → name → age (eligibility/health gate) → mobile → OTP verify
(simulated) → identity e-KYC (simulated Aadhaar-alternative — ID *type* only,
never a number) → Dindi/group + headcount → emergency contact → medical flags
→ confirm → verification receipt → QR Yatra Pass.

Simulated verification ONLY: the OTP accepts any digits and the e-KYC never
asks for or stores a real Aadhaar number. On completion a Yatra ID is issued
and a pass link (rendered as an RFID-style QR pass in the web app) is returned.
The pass is the pilgrim's headcount token, SOS identity, and lost-and-found key.
"""
from __future__ import annotations
import re
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.config import get_settings
from agent import persistence

# Ordered intake stages. "otp" and "ekyc" are verification steps (no stored
# field of their own); every other pre-confirm stage stores one field.
_ORDER = ["yatra", "name", "age", "phone", "otp", "ekyc",
          "group", "emergency", "medical", "confirm"]
_NEXT = {a: b for a, b in zip(_ORDER, _ORDER[1:])}

# Stages that mean "an intake is in progress". Anything else (None, "done", a
# cancelled/unknown value) means we should start a fresh registration.
_IN_PROGRESS_STAGES = set(_ORDER)

_YATRA_NAME = {
    "pandharpur": {"mr": "पंढरपूर वारी", "hi": "पंढरपुर वारी", "en": "Pandharpur Wari"},
    "kumbh": {"mr": "सिंहस्थ कुंभमेळा (नाशिक)", "hi": "सिंहस्थ कुंभ (नासिक)", "en": "Simhastha Kumbh (Nashik)"},
}

_PROMPTS = {
    "yatra": {
        "mr": "चला यात्रा पास काढूया! 🚩 तुम्ही कोणत्या यात्रेसाठी नोंदणी करत आहात?\n\n**1.** पंढरपूर वारी\n**2.** सिंहस्थ कुंभमेळा (नाशिक)\n\n1 किंवा 2 लिहा.",
        "hi": "चलिए यात्रा पास बनाते हैं! 🚩 आप किस यात्रा के लिए पंजीकरण कर रहे हैं?\n\n**1.** पंढरपुर वारी\n**2.** सिंहस्थ कुंभ (नासिक)\n\n1 या 2 लिखें।",
        "en": "Let's create your yatra pass! 🚩 Which yatra are you registering for?\n\n**1.** Pandharpur Wari\n**2.** Simhastha Kumbh (Nashik)\n\nReply 1 or 2.",
    },
    "name": {
        "mr": "तुमचे **पूर्ण नाव** (आधार/ओळखपत्राप्रमाणे)?",
        "hi": "आपका **पूरा नाम** (पहचान पत्र के अनुसार)?",
        "en": "Your **full name** (as on your ID)?",
    },
    "age": {
        "mr": "तुमचे **वय** किती? (वर्षांमध्ये)",
        "hi": "आपकी **उम्र** क्या है? (वर्षों में)",
        "en": "Your **age**? (in years)",
    },
    "phone": {
        "mr": "तुमचा **१०-अंकी मोबाइल क्रमांक**? (यात्रेदरम्यान हाच वापरला जाईल)",
        "hi": "आपका **10-अंकों का मोबाइल नंबर**? (यात्रा के दौरान यही उपयोग होगा)",
        "en": "Your **10-digit mobile number**? (this is the number you'll carry on the yatra)",
    },
    "group": {
        "mr": "तुम्ही कोणत्या **दिंडी/गटा**सोबत आहात आणि **किती जण**? (उदा. 'आळंदी दिंडी, ४' — एकटे असल्यास 'एकटा')",
        "hi": "आप किस **दिंडी/समूह** के साथ हैं और **कितने लोग**? (जैसे 'आळंदी दिंडी, 4' — अकेले हों तो 'अकेला')",
        "en": "Which **Dindi / group** are you with, and **how many people**? (e.g. 'Alandi Dindi, 4' — type 'solo' if alone)",
    },
    "emergency": {
        "mr": "**आपत्कालीन संपर्क** — नाव आणि मोबाइल क्रमांक. (उदा. 'सुनील ९८XXXXXXXX')",
        "hi": "**आपातकालीन संपर्क** — नाम और मोबाइल नंबर। (जैसे 'सुनील 98XXXXXXXX')",
        "en": "**Emergency contact** — a name and mobile number. (e.g. 'Sunil 98XXXXXXXX')",
    },
    "medical": {
        "mr": "सुरक्षेसाठी काही **वैद्यकीय बाब** नोंदवायची? (उदा. मधुमेह, हृदयविकार, वृद्ध, गर्भवती) — नसल्यास 'काही नाही'.",
        "hi": "सुरक्षा के लिए कोई **चिकित्सीय जानकारी**? (जैसे मधुमेह, हृदय रोग, बुज़ुर्ग, गर्भवती) — न हो तो 'कुछ नहीं'.",
        "en": "Any **medical conditions** to note for your safety? (e.g. diabetes, heart condition, elderly, pregnancy) — type 'none' if not.",
    },
}

# OTP prompt (asked when advancing INTO the otp stage — after the phone is
# captured). {phone} is masked to the last 2 digits.
_OTP_PROMPT = {
    "mr": "📲 **+91-••••••{tail}** वर एक OTP पाठवला आहे. **६-अंकी कोड** लिहा.\n(हे प्रात्यक्षिक आहे — कोणतेही ६ अंक चालतील.)",
    "hi": "📲 **+91-••••••{tail}** पर एक OTP भेजा गया है। **6-अंकों का कोड** लिखें।\n(यह डेमो है — कोई भी 6 अंक चलेंगे।)",
    "en": "📲 An OTP has been sent to **+91-••••••{tail}**. Enter the **6-digit code**.\n(This is a demo — any 6 digits work.)",
}

# e-KYC prompt (asked when advancing INTO the ekyc stage).
_EKYC_PROMPT = {
    "mr": "🔐 ओळख पडताळणीसाठी तुम्ही कोणते **ओळखपत्र** वापराल? **आधार / मतदार ओळखपत्र / पासपोर्ट / वाहन परवाना** — फक्त प्रकार लिहा.\n(गोपनीयता: आम्ही तुमचा आधार क्रमांक विचारत नाही किंवा साठवत नाही.)",
    "hi": "🔐 पहचान सत्यापन के लिए आप कौन-सा **पहचान पत्र** उपयोग करेंगे? **आधार / वोटर आईडी / पासपोर्ट / ड्राइविंग लाइसेंस** — केवल प्रकार लिखें।\n(गोपनीयता: हम आपका आधार नंबर नहीं पूछते और न ही सहेजते हैं।)",
    "en": "🔐 For identity verification, which **ID** will you use? **Aadhaar / Voter ID / Passport / Driving licence** — just the type.\n(Privacy: we never ask for or store your Aadhaar number.)",
}

# Acknowledgement lines prepended to the NEXT prompt after a verify step.
_ACK = {
    "otp": {"mr": "✅ मोबाइल क्रमांक पडताळला.", "hi": "✅ मोबाइल नंबर सत्यापित।", "en": "✅ Mobile number verified."},
    "ekyc": {"mr": "✅ ओळख पडताळली (e-KYC — प्रात्यक्षिक, आधार क्रमांक साठवलेला नाही).",
             "hi": "✅ पहचान सत्यापित (e-KYC — डेमो, आधार नंबर नहीं सहेजा गया)।",
             "en": "✅ Identity verified via e-KYC (demo — no Aadhaar number stored)."},
}

_ELIGIBILITY_NOTE = {
    "mr": "⚠️ १३ वर्षांखालील व ७० वर्षांवरील यात्रेकरूंसाठी सोबती/वैद्यकीय दाखला आवश्यक — तुमचा पास 'अतिरिक्त काळजी' म्हणून चिन्हांकित केला जाईल.",
    "hi": "⚠️ 13 वर्ष से कम और 70 वर्ष से अधिक यात्रियों के लिए साथी/चिकित्सा प्रमाण ज़रूरी — आपका पास 'अतिरिक्त देखभाल' के रूप में चिह्नित होगा।",
    "en": "⚠️ Pilgrims under 13 or over 70 need a guardian / medical clearance — your pass will be flagged for extra care.",
}

_INVALID = {
    "yatra": {"mr": "कृपया **1** (पंढरपूर वारी) किंवा **2** (सिंहस्थ कुंभ) लिहा.",
              "hi": "कृपया **1** (पंढरपुर वारी) या **2** (सिंहस्थ कुंभ) लिखें।",
              "en": "Please reply **1** (Pandharpur Wari) or **2** (Simhastha Kumbh)."},
    "age": {"mr": "कृपया वैध वय लिहा (१–१२० वर्षे).", "hi": "कृपया मान्य उम्र लिखें (1–120 वर्ष)।", "en": "Please enter a valid age (1–120 years)."},
    "phone": {"mr": "कृपया वैध १०-अंकी भारतीय मोबाइल क्रमांक लिहा.", "hi": "कृपया मान्य 10-अंकों का भारतीय मोबाइल नंबर लिखें।", "en": "Please enter a valid 10-digit Indian mobile number."},
    "otp": {"mr": "कृपया ४–६ अंकांचा OTP लिहा.", "hi": "कृपया 4–6 अंकों का OTP लिखें।", "en": "Please enter the 4–6 digit OTP."},
    "emergency": {"mr": "कृपया नाव व वैध १०-अंकी क्रमांक लिहा (उदा. 'सुनील ९८XXXXXXXX').",
                  "hi": "कृपया नाम और मान्य 10-अंकों का नंबर लिखें (जैसे 'सुनील 98XXXXXXXX')।",
                  "en": "Please give a name and a valid 10-digit number (e.g. 'Sunil 98XXXXXXXX')."},
}

_NONE_WORDS = {"none", "no", "nil", "na", "n/a", "solo", "alone",
               "काही नाही", "नाही", "एकटा", "एकटी", "एकटे",
               "कुछ नहीं", "नहीं", "अकेला", "अकेले", "कोई नहीं"}


def _last_user(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content).strip()
    return ""


def _is_yes(text: str) -> bool:
    return text.strip().lower() in ("yes", "y", "हो", "हाँ", "haan", "ho", "confirm", "ok", "okay", "बरोबर", "सही")


def _is_none(text: str) -> bool:
    return text.strip().lower() in _NONE_WORDS


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _valid_mobile(text: str) -> str | None:
    """Return a clean 10-digit Indian mobile, or None. Accepts +91/0 prefixes."""
    d = _digits(text)
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else None


def _parse_yatra(text: str, default: str | None) -> str | None:
    t = text.strip().lower()
    if t in ("1", "१") or any(k in t for k in ("pandhar", "wari", "पंढर", "वारी", "आषाढी")):
        return "pandharpur"
    if t in ("2", "२") or any(k in t for k in ("kumbh", "simhast", "nashik", "nasik", "कुंभ", "सिंहस्थ", "नाशिक", "नासिक")):
        return "kumbh"
    if _is_yes(text) and default:
        return default
    return None


def _parse_group(text: str) -> tuple[str, int]:
    """Return (group_name, size). 'solo'/'none' → ('Solo', 1)."""
    if _is_none(text):
        return ("Solo", 1)
    nums = re.findall(r"\d+", text)
    size = int(nums[-1]) if nums else 1
    name = re.sub(r"[,;]?\s*\d+\s*$", "", text).strip(" ,;-") or text.strip()
    return (name or "—", max(size, 1))


def _mask_phone(phone: str) -> str:
    d = _digits(phone)
    return d[-2:] if len(d) >= 2 else "00"


def _confirm_prompt(fields: dict, lang: str) -> str:
    yatra = fields.get("yatra", "pandharpur")
    yname = _YATRA_NAME.get(yatra, {}).get(lang, yatra)
    rows = {
        "mr": [("यात्रा", yname), ("नाव", fields.get("name", "")), ("वय", fields.get("age", "")),
               ("मोबाइल", fields.get("phone", "")), ("ओळख (e-KYC)", fields.get("id_type", "")),
               ("दिंडी/गट", f"{fields.get('group_name','')} ({fields.get('group_size',1)})"),
               ("आपत्कालीन संपर्क", fields.get("emergency_contact", "")),
               ("वैद्यकीय", fields.get("medical_flags", "—"))],
        "hi": [("यात्रा", yname), ("नाम", fields.get("name", "")), ("उम्र", fields.get("age", "")),
               ("मोबाइल", fields.get("phone", "")), ("पहचान (e-KYC)", fields.get("id_type", "")),
               ("दिंडी/समूह", f"{fields.get('group_name','')} ({fields.get('group_size',1)})"),
               ("आपातकालीन संपर्क", fields.get("emergency_contact", "")),
               ("चिकित्सीय", fields.get("medical_flags", "—"))],
        "en": [("Yatra", yname), ("Name", fields.get("name", "")), ("Age", fields.get("age", "")),
               ("Mobile", fields.get("phone", "")), ("Identity (e-KYC)", fields.get("id_type", "")),
               ("Dindi/Group", f"{fields.get('group_name','')} ({fields.get('group_size',1)})"),
               ("Emergency", fields.get("emergency_contact", "")),
               ("Medical", fields.get("medical_flags", "—"))],
    }[lang]
    summary = "\n".join(f"- **{k}:** {v}" for k, v in rows)
    head = {"mr": "कृपया तपशील तपासा आणि पास तयार करण्यासाठी **'हो'** लिहा:",
            "hi": "कृपया विवरण जाँचें और पास बनाने के लिए **'हाँ'** लिखें:",
            "en": "Please check your details and reply **'yes'** to issue your pass:"}[lang]
    return f"{head}\n\n{summary}"


def _issued_message(yatra_id: str, pass_url: str, fields: dict, lang: str) -> str:
    """Verification receipt + the QR pass link (single streamed message)."""
    checks = {
        "mr": ["⏳ तपशील पडताळत आहे…", "✅ पात्रता तपासली", "✅ e-KYC पूर्ण (प्रात्यक्षिक)", "✅ यात्रा RFID वाटप केले"],
        "hi": ["⏳ विवरण सत्यापित हो रहा है…", "✅ पात्रता जाँची", "✅ e-KYC पूर्ण (डेमो)", "✅ यात्रा RFID आवंटित"],
        "en": ["⏳ Verifying details…", "✅ Eligibility checked", "✅ e-KYC complete (demo)", "✅ Yatra RFID allotted"],
    }[lang]
    done = {"mr": f"🎉 **नोंदणी पूर्ण!** तुमचा **यात्रा ID: {yatra_id}**\n\n[📲 तुमचा QR यात्रा पास उघडा]({pass_url})\n\nचेकपॉइंटवर हा पास दाखवा — तो हजेरी नोंदतो आणि आणीबाणीत तुमची ओळख पटवतो.",
            "hi": f"🎉 **पंजीकरण पूरा!** आपका **यात्रा ID: {yatra_id}**\n\n[📲 अपना QR यात्रा पास खोलें]({pass_url})\n\nचेकपॉइंट पर यह पास दिखाएं — यह हेडकाउंट करता है और आपात स्थिति में आपकी पहचान बताता है।",
            "en": f"🎉 **Registration complete!** Your **Yatra ID: {yatra_id}**\n\n[📲 Open your QR yatra pass]({pass_url})\n\nShow this pass at checkpoints — it does headcount and identifies you in an emergency."}[lang]
    return "\n".join(checks) + "\n\n" + done


async def registration(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    user_id = state.get("user_id")
    stage = state.get("reg_stage")
    fields = dict(state.get("reg_fields") or {})

    def _emit(reply: str, *, reg_stage, reg_fields, active_yatra=None) -> YatraState:
        out: YatraState = {**state, "current_node": "registration", "reg_stage": reg_stage,
                           "reg_fields": reg_fields, "messages": messages + [AIMessage(content=reply)]}
        if active_yatra is not None:
            out["active_yatra"] = active_yatra
        return out

    def _prompt_for(next_stage: str, *, ack: str = "") -> str:
        """Build the prompt shown when entering `next_stage` (with optional ack)."""
        if next_stage == "otp":
            body = _OTP_PROMPT[lang].format(tail=_mask_phone(fields.get("phone", "")))
        elif next_stage == "ekyc":
            body = _EKYC_PROMPT[lang]
        elif next_stage == "confirm":
            body = _confirm_prompt(fields, lang)
        else:
            body = _PROMPTS[next_stage][lang]
        return f"{ack}\n\n{body}" if ack else body

    # Start (or restart) intake — ask the first question. Do not consume the
    # trigger turn as an answer. A prior done/cancelled/unknown stage begins a
    # clean intake with empty fields.
    if stage not in _IN_PROGRESS_STAGES:
        return _emit(_PROMPTS["yatra"][lang], reg_stage="yatra", reg_fields={})

    answer = _last_user(messages)

    # ── yatra selection ──────────────────────────────────────────────
    if stage == "yatra":
        chosen = _parse_yatra(answer, state.get("active_yatra"))
        if not chosen:
            return _emit(_INVALID["yatra"][lang], reg_stage="yatra", reg_fields=fields)
        fields["yatra"] = chosen
        return _emit(_prompt_for("name"), reg_stage="name", reg_fields=fields, active_yatra=chosen)

    # ── name ─────────────────────────────────────────────────────────
    if stage == "name":
        fields["name"] = answer
        return _emit(_prompt_for("age"), reg_stage="age", reg_fields=fields)

    # ── age (eligibility / health gate) ──────────────────────────────
    if stage == "age":
        nums = re.findall(r"\d+", answer)
        age = int(nums[0]) if nums else 0
        if not (1 <= age <= 120):
            return _emit(_INVALID["age"][lang], reg_stage="age", reg_fields=fields)
        fields["age"] = str(age)
        ack = _ELIGIBILITY_NOTE[lang] if (age < 13 or age > 70) else ""
        if age < 13 or age > 70:
            fields["medical_flags"] = (fields.get("medical_flags", "") + "; needs guardian/medical clearance").strip("; ")
        return _emit(_prompt_for("phone", ack=ack), reg_stage="phone", reg_fields=fields)

    # ── phone → send simulated OTP ───────────────────────────────────
    if stage == "phone":
        mobile = _valid_mobile(answer)
        if not mobile:
            return _emit(_INVALID["phone"][lang], reg_stage="phone", reg_fields=fields)
        fields["phone"] = mobile
        return _emit(_prompt_for("otp"), reg_stage="otp", reg_fields=fields)

    # ── OTP verify (simulated) ───────────────────────────────────────
    if stage == "otp":
        code = _digits(answer)
        if not (4 <= len(code) <= 6):
            return _emit(_INVALID["otp"][lang], reg_stage="otp", reg_fields=fields)
        fields["mobile_verified"] = True
        return _emit(_prompt_for("ekyc", ack=_ACK["otp"][lang]), reg_stage="ekyc", reg_fields=fields)

    # ── e-KYC identity verify (simulated — ID type only) ─────────────
    if stage == "ekyc":
        t = answer.strip().lower()
        id_type = ("Aadhaar" if ("aadhaar" in t or "aadhar" in t or "आधार" in answer)
                   else "Voter ID" if ("voter" in t or "epic" in t or "मतदार" in answer or "वोटर" in answer)
                   else "Passport" if ("passport" in t or "पासपोर्ट" in answer)
                   else "Driving licence" if ("driv" in t or "dl" == t or "लाइसेंस" in answer or "परवाना" in answer)
                   else "Govt ID")
        fields["id_type"] = id_type
        fields["ekyc_verified"] = True
        return _emit(_prompt_for("group", ack=_ACK["ekyc"][lang]), reg_stage="group", reg_fields=fields)

    # ── Dindi/group + headcount ──────────────────────────────────────
    if stage == "group":
        name, size = _parse_group(answer)
        fields["group_name"] = name
        fields["group_size"] = size
        return _emit(_prompt_for("emergency"), reg_stage="emergency", reg_fields=fields)

    # ── emergency contact ────────────────────────────────────────────
    if stage == "emergency":
        mobile = _valid_mobile(answer)
        if not mobile:
            return _emit(_INVALID["emergency"][lang], reg_stage="emergency", reg_fields=fields)
        name = re.sub(r"[+\d\s\-]+", " ", answer).strip(" ,;-") or "—"
        fields["emergency_contact"] = f"{name} {mobile}".strip()
        return _emit(_prompt_for("medical"), reg_stage="medical", reg_fields=fields)

    # ── medical flags ────────────────────────────────────────────────
    if stage == "medical":
        med = "none" if _is_none(answer) else answer
        existing = fields.get("medical_flags", "")
        # Preserve any eligibility flag set at the age step.
        fields["medical_flags"] = (f"{med}; {existing}".strip("; ") if existing and med != "none"
                                   else existing or med)
        return _emit(_confirm_prompt(fields, lang), reg_stage="confirm", reg_fields=fields)

    # ── confirm → issue pass, or cancel ──────────────────────────────
    if stage == "confirm":
        if _is_yes(answer):
            yatra = fields.get("yatra") or state.get("active_yatra") or "pandharpur"
            yatra_id = await persistence.create_registration(
                user_id, yatra=yatra, name=fields.get("name", ""), phone=fields.get("phone", ""),
                age=fields.get("age", ""), id_type=fields.get("id_type", ""),
                group_name=fields.get("group_name", ""), group_size=fields.get("group_size", 1),
                emergency_contact=fields.get("emergency_contact", ""),
                medical_flags=fields.get("medical_flags", ""),
                mobile_verified=bool(fields.get("mobile_verified")),
                ekyc_verified=bool(fields.get("ekyc_verified")))
            pass_url = f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/pass?id={yatra_id}"
            return _emit(_issued_message(yatra_id, pass_url, fields, lang), reg_stage="done", reg_fields=fields)
        cancel = {"mr": "नोंदणी रद्द केली. पुन्हा सुरू करण्यासाठी 'नोंदणी' लिहा.",
                  "hi": "पंजीकरण रद्द किया गया। फिर से शुरू करने के लिए 'पंजीकरण' लिखें।",
                  "en": "Registration cancelled. Type 'register' to start again."}[lang]
        return _emit(cancel, reg_stage="done", reg_fields=fields)

    # Unknown stage — restart cleanly.
    return _emit(_PROMPTS["yatra"][lang], reg_stage="yatra", reg_fields={})
