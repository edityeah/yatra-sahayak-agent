"""registration activity — multi-turn yatra-pass intake with simulated
verification, modelled on the Char Dham Yatra registration (UTDB tourist-care
portal) and the Amarnath Yatra permit (SASB), issued in a DigiYatra-style
per-member model.

Flow: yatra → primary (name → age → mobile → OTP → e-KYC → Dindi → emergency →
medical) → "add family member?" loop (name → age, repeats) → confirm →
verification receipt → ONE pass per person, all linked by a shared group_id,
viewable together in the device wallet.

Simulated verification ONLY: OTP accepts any digits; e-KYC never asks for or
stores a real Aadhaar number. Each person gets their own Yatra ID + QR pass
(the headcount token, SOS identity, and lost-and-found key).
"""
from __future__ import annotations
import re
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.config import get_settings
from agent import persistence

# Ordered intake stages for the PRIMARY registrant. "otp"/"ekyc" are verify
# steps; "add_member" starts the family loop; "member_age" is a sub-stage.
_ORDER = ["yatra", "name", "age", "phone", "otp", "ekyc",
          "group", "emergency", "medical", "add_member", "confirm"]
_NEXT = {a: b for a, b in zip(_ORDER, _ORDER[1:])}

# Stages that mean "an intake is in progress". Anything else (None, "done", a
# cancelled/unknown value) means we should start a fresh registration.
_IN_PROGRESS_STAGES = set(_ORDER) | {"member_age"}

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
        "mr": "तुम्ही कोणत्या **दिंडी/गटा**सोबत चालत आहात? नसल्यास 'काही नाही'.",
        "hi": "आप किस **दिंडी/समूह** के साथ चल रहे हैं? न हो तो 'कुछ नहीं'.",
        "en": "Which **Dindi / group** are you walking with? Type 'none' if not with one.",
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
    "add_member": {
        "mr": "तुमच्यासोबत **कुटुंबातील कोणी** यात्रेला येत आहे का? त्यांचे **नाव** लिहा, किंवा पूर्ण करण्यासाठी **'पूर्ण'** लिहा.",
        "hi": "क्या आपके साथ **परिवार का कोई सदस्य** यात्रा कर रहा है? उनका **नाम** लिखें, या पूरा करने के लिए **'पूर्ण'** लिखें।",
        "en": "Is a **family member** travelling with you? Reply their **name**, or **'done'** to finish.",
    },
}

_OTP_PROMPT = {
    "mr": "📲 **+91-••••••{tail}** वर एक OTP पाठवला आहे. **६-अंकी कोड** लिहा.\n(हे प्रात्यक्षिक आहे — कोणतेही ६ अंक चालतील.)",
    "hi": "📲 **+91-••••••{tail}** पर एक OTP भेजा गया है। **6-अंकों का कोड** लिखें।\n(यह डेमो है — कोई भी 6 अंक चलेंगे।)",
    "en": "📲 An OTP has been sent to **+91-••••••{tail}**. Enter the **6-digit code**.\n(This is a demo — any 6 digits work.)",
}

_EKYC_PROMPT = {
    "mr": "🔐 ओळख पडताळणीसाठी तुम्ही कोणते **ओळखपत्र** वापराल? **आधार / मतदार ओळखपत्र / पासपोर्ट / वाहन परवाना** — फक्त प्रकार लिहा.\n(गोपनीयता: आम्ही तुमचा आधार क्रमांक विचारत नाही किंवा साठवत नाही.)",
    "hi": "🔐 पहचान सत्यापन के लिए आप कौन-सा **पहचान पत्र** उपयोग करेंगे? **आधार / वोटर आईडी / पासपोर्ट / ड्राइविंग लाइसेंस** — केवल प्रकार लिखें।\n(गोपनीयता: हम आपका आधार नंबर नहीं पूछते और न ही सहेजते हैं।)",
    "en": "🔐 For identity verification, which **ID** will you use? **Aadhaar / Voter ID / Passport / Driving licence** — just the type.\n(Privacy: we never ask for or store your Aadhaar number.)",
}

# Member age prompt — {name} is the member just named.
_MEMBER_AGE_PROMPT = {
    "mr": "**{name}** यांचे **वय**? (वर्षांमध्ये)",
    "hi": "**{name}** की **उम्र**? (वर्षों में)",
    "en": "**{name}**'s **age**? (in years)",
}

_MEMBER_ADDED = {
    "mr": "✅ **{name}** जोडले.",
    "hi": "✅ **{name}** जोड़ा गया।",
    "en": "✅ Added **{name}**.",
}

_ACK = {
    "otp": {"mr": "✅ मोबाइल क्रमांक पडताळला.", "hi": "✅ मोबाइल नंबर सत्यापित।", "en": "✅ Mobile number verified."},
    "ekyc": {"mr": "✅ ओळख पडताळली (e-KYC — प्रात्यक्षिक, आधार क्रमांक साठवलेला नाही).",
             "hi": "✅ पहचान सत्यापित (e-KYC — डेमो, आधार नंबर नहीं सहेजा गया)।",
             "en": "✅ Identity verified via e-KYC (demo — no Aadhaar number stored)."},
}

_ELIGIBILITY_NOTE = {
    "mr": "⚠️ १३ वर्षांखालील व ७० वर्षांवरील यात्रेकरूंसाठी सोबती/वैद्यकीय दाखला आवश्यक — पास 'अतिरिक्त काळजी' म्हणून चिन्हांकित केला जाईल.",
    "hi": "⚠️ 13 वर्ष से कम और 70 वर्ष से अधिक यात्रियों के लिए साथी/चिकित्सा प्रमाण ज़रूरी — पास 'अतिरिक्त देखभाल' के रूप में चिह्नित होगा।",
    "en": "⚠️ Pilgrims under 13 or over 70 need a guardian / medical clearance — the pass is flagged for extra care.",
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

# Short, helpful answers when the user asks a question mid-intake instead of
# answering (e.g. "what is a Dindi?"). We reply with this, then re-ask.
_HELP = {
    "yatra": {"mr": "आम्ही दोन यात्रांसाठी पास देतो — पंढरपूर वारी आणि सिंहस्थ कुंभ. तुम्ही ज्या यात्रेला जात आहात त्यासाठी 1 किंवा 2 लिहा.",
              "hi": "हम दो यात्राओं के लिए पास देते हैं — पंढरपुर वारी और सिंहस्थ कुंभ। आप जिस यात्रा में जा रहे हैं उसके लिए 1 या 2 लिखें।",
              "en": "We issue passes for two yatras — Pandharpur Wari and Simhastha Kumbh. Reply 1 or 2 for the one you're joining."},
    "name": {"mr": "ओळखपत्रावर असलेले तुमचे पूर्ण नाव लिहा, म्हणजे पास तुमच्या ओळखीशी जुळेल.",
             "hi": "पहचान पत्र पर छपा आपका पूरा नाम लिखें, ताकि पास आपकी पहचान से मेल खाए।",
             "en": "Type your full name as printed on your ID, so the pass matches your identity."},
    "age": {"mr": "वय वर्षांमध्ये — यामुळे अधिक काळजी लागणाऱ्या यात्रेकरूंना चिन्हांकित करता येते.",
            "hi": "उम्र वर्षों में — इससे अधिक देखभाल वाले यात्रियों को चिह्नित किया जाता है।",
            "en": "Your age in years — it helps us flag pilgrims who may need extra care."},
    "phone": {"mr": "तुमचा मोबाइल क्रमांक — यात्रेदरम्यान तुमच्याशी संपर्क साधण्यासाठी वापरला जाईल.",
              "hi": "आपका मोबाइल नंबर — यात्रा के दौरान आपसे संपर्क के लिए उपयोग होगा।",
              "en": "Your mobile number — we use it to reach you during the yatra, especially in an emergency."},
    "otp": {"mr": "तुमचा मोबाइल तुमचाच आहे हे तपासण्यासाठी पाठवलेला कोड. हे प्रात्यक्षिक आहे — कोणतेही ६ अंक चालतील.",
            "hi": "यह जाँचने के लिए कोड कि मोबाइल आपका ही है। यह डेमो है — कोई भी 6 अंक चलेंगे।",
            "en": "A code we 'sent' to confirm the mobile is yours. This is a demo — any 6 digits work."},
    "ekyc": {"mr": "e-KYC फक्त ओळखीचा प्रकार तपासते — आम्ही आधार क्रमांक घेत नाही. आधार / मतदार ओळखपत्र / पासपोर्ट / वाहन परवाना यापैकी एक लिहा.",
             "hi": "e-KYC केवल पहचान का प्रकार जाँचता है — हम आधार नंबर नहीं लेते। आधार / वोटर आईडी / पासपोर्ट / ड्राइविंग लाइसेंस में से एक लिखें।",
             "en": "e-KYC just confirms the type of ID — we never take your Aadhaar number. Reply Aadhaar, Voter ID, Passport, or Driving licence."},
    "group": {"mr": "दिंडी म्हणजे पालखीसोबत एकत्र चालणारा, अभंग गाणारा वारकऱ्यांचा गट. तुम्ही एखाद्या दिंडीसोबत असाल तर तिचे नाव लिहा; नसल्यास 'काही नाही'.",
              "hi": "दिंडी यानी पालकी के साथ मिलकर चलने वाला, अभंग गाने वाला वारकरियों का समूह। आप किसी दिंडी के साथ हों तो उसका नाम लिखें; न हों तो 'कुछ नहीं'.",
              "en": "A Dindi is a group of Warkari pilgrims who walk together with the palkhi, singing abhangs. If you're walking with one, type its name; otherwise type 'none'."},
    "emergency": {"mr": "यात्रेत काही झाल्यास ज्याला फोन करता येईल अशी व्यक्ती — त्यांचे नाव व मोबाइल क्रमांक द्या.",
                  "hi": "यात्रा में कुछ होने पर जिसे फोन कर सकें ऐसा व्यक्ति — उनका नाम और मोबाइल नंबर दें।",
                  "en": "Someone we can call if something happens to you on the yatra — give their name and mobile number."},
    "medical": {"mr": "आणीबाणीत महत्त्वाची ठरणारी कोणतीही वैद्यकीय बाब (मधुमेह, हृदयविकार, गर्भवती, वृद्ध) — किंवा 'काही नाही'.",
                "hi": "आपात स्थिति में मायने रखने वाली कोई चिकित्सीय बात (मधुमेह, हृदय रोग, गर्भवती, बुज़ुर्ग) — या 'कुछ नहीं'.",
                "en": "Any health condition worth knowing in an emergency (diabetes, heart condition, pregnancy, elderly) — or 'none'."},
    "add_member": {"mr": "तुमच्यासोबत चालणाऱ्या कुटुंबातील प्रत्येकाला स्वतःचा पास मिळावा म्हणून त्यांचे नाव जोडा. सदस्याचे नाव लिहा, किंवा पूर्ण करण्यासाठी 'पूर्ण'.",
                   "hi": "आपके साथ चलने वाले परिवार के हर सदस्य को अपना पास मिले, इसके लिए उनका नाम जोड़ें। सदस्य का नाम लिखें, या पूरा करने के लिए 'पूर्ण'.",
                   "en": "Add family members walking with you so each gets their own pass. Reply a member's name, or 'done' to finish."},
    "member_age": {"mr": "तुम्ही जोडत असलेल्या कुटुंब सदस्याचे वय (वर्षांमध्ये).",
                   "hi": "आप जिस परिवार सदस्य को जोड़ रहे हैं उसकी उम्र (वर्षों में)।",
                   "en": "The age (in years) of the family member you're adding."},
    "confirm": {"mr": "वरील तपशील तपासा. पास तयार करण्यासाठी 'हो' लिहा, किंवा काय बदलायचे ते सांगा.",
                "hi": "ऊपर के विवरण जाँचें। पास बनाने के लिए 'हाँ' लिखें, या बताएं क्या बदलना है।",
                "en": "Check the details above. Reply 'yes' to issue the pass(es), or tell me what to change."},
}
_GENERIC_HELP = {"mr": "ठीक आहे — नोंदणी पुढे चालू ठेवूया.",
                 "hi": "ठीक है — पंजीकरण आगे बढ़ाते हैं।",
                 "en": "No problem — let's continue your registration."}

# Question openers across en / hi / mr (romanised + Devanagari).
_Q_STARTS = ("what", "why", "how", "who", "when", "where", "which", "can i", "do i", "should i",
             "is it", "are ", "kya", "kyu", "kyun", "kaise", "kaisa", "kaun", "kab", "kahan", "matlab",
             "kaay", "kay ", "ka ", "kase", "kon", "kuthe", "kadhi", "mhanje",
             "काय", "का ", "कशी", "कसे", "कोण", "कुठे", "कधी", "म्हणजे",
             "क्या", "क्यों", "कैसे", "कौन", "कब", "कहां", "मतलब")


def _looks_like_question(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if "?" in t or "？" in t:
        return True
    return any(t.startswith(w) for w in _Q_STARTS)


_NONE_WORDS = {"none", "no", "nil", "na", "n/a", "solo", "alone",
               "काही नाही", "नाही", "एकटा", "एकटी", "एकटे",
               "कुछ नहीं", "नहीं", "अकेला", "अकेले", "कोई नहीं"}
_DONE_WORDS = {"done", "finish", "finished", "no", "nope", "that's all", "thats all", "bas",
               "पूर्ण", "झाले", "बस", "नाही", "हो गया", "समाप्त", "नहीं"}


def _last_user(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content).strip()
    return ""


def _is_yes(text: str) -> bool:
    return text.strip().lower() in ("yes", "y", "हो", "हाँ", "haan", "ho", "confirm", "ok", "okay", "बरोबर", "सही")


def _is_none(text: str) -> bool:
    return text.strip().lower() in _NONE_WORDS


def _is_done(text: str) -> bool:
    return text.strip().lower() in _DONE_WORDS


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _valid_mobile(text: str) -> str | None:
    d = _digits(text)
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else None


def _valid_age(text: str) -> int | None:
    nums = re.findall(r"\d+", text or "")
    if not nums:
        return None
    age = int(nums[0])
    return age if 1 <= age <= 120 else None


def _parse_yatra(text: str, default: str | None) -> str | None:
    t = text.strip().lower()
    if t in ("1", "१") or any(k in t for k in ("pandhar", "wari", "पंढर", "वारी", "आषाढी")):
        return "pandharpur"
    if t in ("2", "२") or any(k in t for k in ("kumbh", "simhast", "nashik", "nasik", "कुंभ", "सिंहस्थ", "नाशिक", "नासिक")):
        return "kumbh"
    if _is_yes(text) and default:
        return default
    return None


def _mask_phone(phone: str) -> str:
    d = _digits(phone)
    return d[-2:] if len(d) >= 2 else "00"


def _eligibility_flag(age: int) -> str:
    return "needs guardian/medical clearance" if (age < 13 or age > 70) else ""


def _confirm_prompt(fields: dict, lang: str) -> str:
    yatra = fields.get("yatra", "pandharpur")
    yname = _YATRA_NAME.get(yatra, {}).get(lang, yatra)
    members = fields.get("members", [])
    labels = {
        "mr": {"y": "यात्रा", "grp": "दिंडी/गट", "em": "आपत्कालीन संपर्क", "who": "पास ({n}):", "yrs": "वर्षे"},
        "hi": {"y": "यात्रा", "grp": "दिंडी/समूह", "em": "आपातकालीन संपर्क", "who": "पास ({n}):", "yrs": "वर्ष"},
        "en": {"y": "Yatra", "grp": "Dindi/Group", "em": "Emergency", "who": "Passes ({n}):", "yrs": "yrs"},
    }[lang]
    people = [f"{fields.get('name','')} ({fields.get('age','')} {labels['yrs']})"]
    people += [f"{m['name']} ({m['age']} {labels['yrs']})" for m in members]
    who = labels["who"].format(n=len(people)) + "\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(people))
    lines = [
        f"- **{labels['y']}:** {yname}",
        f"- **{labels['grp']}:** {fields.get('group_name') or '—'}",
        f"- **{labels['em']}:** {fields.get('emergency_contact','')}",
        f"- **{who}**",
    ]
    head = {"mr": "कृपया तपशील तपासा आणि पास तयार करण्यासाठी **'हो'** लिहा:",
            "hi": "कृपया विवरण जाँचें और पास बनाने के लिए **'हाँ'** लिखें:",
            "en": "Please check the details and reply **'yes'** to issue the pass(es):"}[lang]
    return f"{head}\n\n" + "\n".join(lines)


def _issued_message(issued: list[tuple[str, str]], wallet_url: str, lang: str) -> str:
    """issued = [(name, yatra_id), ...] (primary first)."""
    checks = {
        "mr": ["⏳ तपशील पडताळत आहे…", "✅ पात्रता तपासली", "✅ e-KYC पूर्ण (प्रात्यक्षिक)", f"✅ {len(issued)} यात्रा RFID पास वाटप केले"],
        "hi": ["⏳ विवरण सत्यापित हो रहा है…", "✅ पात्रता जाँची", "✅ e-KYC पूर्ण (डेमो)", f"✅ {len(issued)} यात्रा RFID पास आवंटित"],
        "en": ["⏳ Verifying details…", "✅ Eligibility checked", "✅ e-KYC complete (demo)", f"✅ {len(issued)} Yatra RFID pass(es) allotted"],
    }[lang]
    rows = "\n".join(f"  {i+1}. **{name}** — {yid}" for i, (name, yid) in enumerate(issued))
    head = {"mr": f"🎉 **नोंदणी पूर्ण!** {len(issued)} पास तयार:",
            "hi": f"🎉 **पंजीकरण पूरा!** {len(issued)} पास बने:",
            "en": f"🎉 **Registration complete!** {len(issued)} pass(es) issued:"}[lang]
    cta = {"mr": f"[📲 सर्व पास उघडा (वॉलेट)]({wallet_url})\n\nप्रत्येक पास वॉलेटमधून डाउनलोड करा किंवा WhatsApp वर पाठवा. चेकपॉइंटवर QR दाखवा.",
           "hi": f"[📲 सभी पास खोलें (वॉलेट)]({wallet_url})\n\nहर पास वॉलेट से डाउनलोड करें या WhatsApp पर भेजें। चेकपॉइंट पर QR दिखाएं।",
           "en": f"[📲 Open all passes (wallet)]({wallet_url})\n\nDownload each pass from the wallet or share it on WhatsApp. Show the QR at checkpoints."}[lang]
    return "\n".join(checks) + "\n\n" + head + "\n" + rows + "\n\n" + cta


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
        if next_stage == "otp":
            body = _OTP_PROMPT[lang].format(tail=_mask_phone(fields.get("phone", "")))
        elif next_stage == "ekyc":
            body = _EKYC_PROMPT[lang]
        elif next_stage == "confirm":
            body = _confirm_prompt(fields, lang)
        else:
            body = _PROMPTS[next_stage][lang]
        return f"{ack}\n\n{body}" if ack else body

    def _reask(st: str) -> str:
        """Re-ask the CURRENT stage's prompt (used after answering a question)."""
        if st == "member_age":
            return _MEMBER_AGE_PROMPT[lang].format(name=fields.get("_pending_name", ""))
        return _prompt_for(st)

    # Start (or restart) intake — ask the first question, empty fields.
    if stage not in _IN_PROGRESS_STAGES:
        return _emit(_PROMPTS["yatra"][lang], reg_stage="yatra", reg_fields={"members": []})

    answer = _last_user(messages)
    fields.setdefault("members", [])

    # The user asked a question instead of answering (e.g. "what is a Dindi?").
    # Answer it briefly, then re-ask the same field — never store the question.
    if _looks_like_question(answer):
        help_text = _HELP.get(stage, {}).get(lang) or _GENERIC_HELP[lang]
        return _emit(f"{help_text}\n\n{_reask(stage)}", reg_stage=stage, reg_fields=fields)

    # ── yatra selection ──────────────────────────────────────────────
    if stage == "yatra":
        chosen = _parse_yatra(answer, state.get("active_yatra"))
        if not chosen:
            return _emit(_INVALID["yatra"][lang], reg_stage="yatra", reg_fields=fields)
        fields["yatra"] = chosen
        return _emit(_prompt_for("name"), reg_stage="name", reg_fields=fields, active_yatra=chosen)

    if stage == "name":
        fields["name"] = answer
        return _emit(_prompt_for("age"), reg_stage="age", reg_fields=fields)

    if stage == "age":
        age = _valid_age(answer)
        if age is None:
            return _emit(_INVALID["age"][lang], reg_stage="age", reg_fields=fields)
        fields["age"] = str(age)
        flag = _eligibility_flag(age)
        if flag:
            fields["medical_flags"] = flag
        ack = _ELIGIBILITY_NOTE[lang] if flag else ""
        return _emit(_prompt_for("phone", ack=ack), reg_stage="phone", reg_fields=fields)

    if stage == "phone":
        mobile = _valid_mobile(answer)
        if not mobile:
            return _emit(_INVALID["phone"][lang], reg_stage="phone", reg_fields=fields)
        fields["phone"] = mobile
        return _emit(_prompt_for("otp"), reg_stage="otp", reg_fields=fields)

    if stage == "otp":
        code = _digits(answer)
        if not (4 <= len(code) <= 6):
            return _emit(_INVALID["otp"][lang], reg_stage="otp", reg_fields=fields)
        fields["mobile_verified"] = True
        return _emit(_prompt_for("ekyc", ack=_ACK["otp"][lang]), reg_stage="ekyc", reg_fields=fields)

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

    if stage == "group":
        fields["group_name"] = "" if _is_none(answer) else answer.strip()
        return _emit(_prompt_for("emergency"), reg_stage="emergency", reg_fields=fields)

    if stage == "emergency":
        mobile = _valid_mobile(answer)
        if not mobile:
            return _emit(_INVALID["emergency"][lang], reg_stage="emergency", reg_fields=fields)
        name = re.sub(r"[+\d\s\-]+", " ", answer).strip(" ,;-") or "—"
        fields["emergency_contact"] = f"{name} {mobile}".strip()
        return _emit(_prompt_for("medical"), reg_stage="medical", reg_fields=fields)

    if stage == "medical":
        med = "none" if _is_none(answer) else answer
        existing = fields.get("medical_flags", "")
        fields["medical_flags"] = (f"{med}; {existing}".strip("; ") if existing and med != "none"
                                   else existing or med)
        # Move into the family-member loop.
        return _emit(_prompt_for("add_member"), reg_stage="add_member", reg_fields=fields)

    # ── family-member loop ───────────────────────────────────────────
    if stage == "add_member":
        if _is_done(answer) or _is_none(answer):
            return _emit(_prompt_for("confirm"), reg_stage="confirm", reg_fields=fields)
        fields["_pending_name"] = answer.strip()
        return _emit(_MEMBER_AGE_PROMPT[lang].format(name=fields["_pending_name"]),
                     reg_stage="member_age", reg_fields=fields)

    if stage == "member_age":
        age = _valid_age(answer)
        if age is None:
            name = fields.get("_pending_name", "")
            return _emit(f"{_INVALID['age'][lang]}\n\n" + _MEMBER_AGE_PROMPT[lang].format(name=name),
                         reg_stage="member_age", reg_fields=fields)
        name = fields.pop("_pending_name", "")
        member = {"name": name, "age": str(age), "medical_flags": _eligibility_flag(age) or "none"}
        fields["members"] = fields.get("members", []) + [member]
        ack = _MEMBER_ADDED[lang].format(name=name)
        if _eligibility_flag(age):
            ack += "\n" + _ELIGIBILITY_NOTE[lang]
        return _emit(_prompt_for("add_member", ack=ack), reg_stage="add_member", reg_fields=fields)

    # ── confirm → issue one pass per person, or cancel ───────────────
    if stage == "confirm":
        if _is_yes(answer):
            yatra = fields.get("yatra") or state.get("active_yatra") or "pandharpur"
            members = fields.get("members", [])
            total = 1 + len(members)
            group_id = persistence.new_group_id() if members else ""
            common = dict(yatra=yatra, group_name=fields.get("group_name", ""), group_size=total,
                          group_id=group_id, emergency_contact=fields.get("emergency_contact", ""),
                          mobile_verified=True, ekyc_verified=True)
            issued: list[tuple[str, str]] = []
            primary_id = await persistence.create_registration(
                user_id, name=fields.get("name", ""), phone=fields.get("phone", ""),
                age=fields.get("age", ""), id_type=fields.get("id_type", ""),
                medical_flags=fields.get("medical_flags", ""), is_primary=True, **common)
            issued.append((fields.get("name", ""), primary_id))
            for m in members:
                mid = await persistence.create_registration(
                    user_id, name=m["name"], phone=fields.get("phone", ""),
                    age=m.get("age", ""), id_type=fields.get("id_type", ""),
                    medical_flags=m.get("medical_flags", "none"), is_primary=False, **common)
                issued.append((m["name"], mid))
            wallet_url = f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/passes?user_id={user_id}"
            return _emit(_issued_message(issued, wallet_url, lang), reg_stage="done", reg_fields=fields)
        cancel = {"mr": "नोंदणी रद्द केली. पुन्हा सुरू करण्यासाठी 'नोंदणी' लिहा.",
                  "hi": "पंजीकरण रद्द किया गया। फिर से शुरू करने के लिए 'पंजीकरण' लिखें।",
                  "en": "Registration cancelled. Type 'register' to start again."}[lang]
        return _emit(cancel, reg_stage="done", reg_fields=fields)

    # Unknown stage — restart cleanly.
    return _emit(_PROMPTS["yatra"][lang], reg_stage="yatra", reg_fields={"members": []})
