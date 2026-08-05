"""Proactive follow-up suggestions appended to an activity reply so the agent
always offers a relevant next step instead of ending the conversation. Rendered
as PLAIN TEXT everywhere (no tappable buttons — those don't render in SwiftChat).
Each phrase is written so, if the user types it, it routes to the intended
activity via the keyword router."""
from __future__ import annotations

_LABEL = {"mr": "पुढे तुम्ही विचारू शकता —", "hi": "आगे आप पूछ सकते हैं —", "en": "You can also ask about —"}
_OR = {"mr": "किंवा", "hi": "या", "en": "or"}

# intent → up to three follow-up prompts (trilingual), cross-linking services.
_SUGGESTIONS = {
    "darshan": {
        "mr": ["मंदिराचा मार्ग", "आज कुठे राहू?", "जवळचे अन्नदान"],
        "hi": ["मंदिर का रास्ता", "आज कहाँ रुकें?", "नज़दीकी अन्नदान"],
        "en": ["Directions to the temple", "Where can I stay tonight?", "Free food nearby"],
    },
    "accommodation": {
        "mr": ["जवळचे अन्नदान", "दर्शन वेळा", "मार्ग नकाशा"],
        "hi": ["नज़दीकी अन्नदान", "दर्शन समय", "मार्ग मानचित्र"],
        "en": ["Free food nearby", "Darshan timings", "Route map"],
    },
    "langar": {
        "mr": ["जवळचे आरोग्य केंद्र", "दर्शन वेळा", "आज कुठे राहू?"],
        "hi": ["नज़दीकी स्वास्थ्य केंद्र", "दर्शन समय", "आज कहाँ रुकें?"],
        "en": ["Nearest medical post", "Darshan timings", "Where can I stay tonight?"],
    },
    "amenity": {
        "mr": ["मदत क्रमांक", "जवळचे पिण्याचे पाणी", "दर्शन वेळा"],
        "hi": ["हेल्पलाइन नंबर", "नज़दीकी पेयजल", "दर्शन समय"],
        "en": ["Helpline numbers", "Nearest drinking water", "Darshan timings"],
    },
    "weather": {
        "mr": ["आजच्या सूचना", "मार्ग नकाशा", "वाहतूक दर"],
        "hi": ["आज की सूचनाएँ", "मार्ग मानचित्र", "परिवहन दर"],
        "en": ["Today's advisories", "Route map", "Transport rates"],
    },
    "helpline": {
        "mr": ["जवळचे आरोग्य केंद्र", "आजच्या सूचना"],
        "hi": ["नज़दीकी स्वास्थ्य केंद्र", "आज की सूचनाएँ"],
        "en": ["Nearest medical post", "Today's advisories"],
    },
    "palkhi": {
        "mr": ["वाहनतळ", "दर्शन वेळा", "आजच्या सूचना"],
        "hi": ["पार्किंग", "दर्शन समय", "आज की सूचनाएँ"],
        "en": ["Parking", "Darshan timings", "Today's advisories"],
    },
    "parking": {
        "mr": ["पालखी मागोवा", "मार्ग नकाशा", "आज कुठे राहू?"],
        "hi": ["पालकी ट्रैकिंग", "मार्ग मानचित्र", "आज कहाँ रुकें?"],
        "en": ["Palkhi tracking", "Route map", "Where can I stay tonight?"],
    },
}


def followup_line(intent: str, lang: str) -> str:
    """The trailing suggestion sentence, or '' if none for this intent. Plain
    prose (comma-joined, no buttons): `💬 You can also ask about — A, B or C.`"""
    lang = lang if lang in ("mr", "hi", "en") else "en"
    opts = _SUGGESTIONS.get(intent, {}).get(lang)
    if not opts:
        return ""
    if len(opts) == 1:
        joined = opts[0]
    else:
        joined = ", ".join(opts[:-1]) + f" {_OR[lang]} " + opts[-1]
    return f"\n\n💬 {_LABEL[lang]} {joined}."
