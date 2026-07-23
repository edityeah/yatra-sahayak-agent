"""i18n — fixed trilingual strings and the language-selection flow.

Marathi and Hindi share the Devanagari script, so we do NOT auto-detect
between them. Instead we ask the user to pick once and remember the choice
via a marker embedded in the selection prompt (re-derived each turn).
"""
from __future__ import annotations
import re

# A phrase that appears ONLY in the language-selection message. Used to
# detect that the user's NEXT turn is answering the language ask.
LANG_ASK_MARKER = "choose your language"


def language_selection_text() -> str:
    return (
        "🙏 **Maharashtra Yatra Sahayak** । यात्रा सहायक ।\n"
        "\n"
        "Please **type one word** to choose your language / कृपया एक शब्द टाइप करा:\n"
        "\n"
        "- Type **Marathi** for मराठी\n"
        "- Type **Hindi** for हिंदी\n"
        "- Type **English** for English\n"
    )


def detect_language_choice(text: str) -> str | None:
    """Return 'mr' | 'hi' | 'en' | None from a language-selection reply."""
    t = (text or "").strip().lower()
    if re.search(r"\bmarathi\b|मराठी", t) or "मराठी" in (text or ""):
        return "mr"
    if re.search(r"\benglish\b|angrezi|\beng\b", t):
        return "hi" if re.search(r"\bhindi\b", t) else "en"
    if re.search(r"\bhindi\b", t) or "हिंदी" in (text or ""):
        return "hi"
    return None


# Short language-name labels for prompts.
LANG_NAME = {"mr": "Marathi", "hi": "Hindi", "en": "English"}
