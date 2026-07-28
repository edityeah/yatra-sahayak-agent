"""weather activity — route weather from the caller's origin to the yatra
destination, entirely IN CHAT.

Origin resolution, in order:
  1. A location the pilgrim shared natively in the chat (SwiftChat location
     message) → state["shared_location"] = {"lat", "lng"}.
  2. A city they named or picked by number from the list we offered.
  3. Neither → ask them to share their location OR reply with a starting city.
     We set state["awaiting"]="weather_origin" so the follow-up (a location
     message, or a bare "Pune"/"2") routes straight back here.

No webview and no simulated button chips — the ask is plain chat text, and the
location comes through SwiftChat's own location-sharing.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.seed import t
from agent import route_weather as rw

_YATRA_NAME = {
    "pandharpur": {"mr": "पंढरपूर वारी", "hi": "पंढरपुर वारी", "en": "Pandharpur Wari"},
    "kumbh": {"mr": "सिंहस्थ कुंभ", "hi": "सिंहस्थ कुंभ", "en": "Simhastha Kumbh"},
}
_HEADER = {"mr": "🌦️ **तुमच्या मार्गावरील हवामान**", "hi": "🌦️ **आपके मार्ग का मौसम**", "en": "🌦️ **Weather on your route**"}

# The origin cities we offer, in a fixed order (also the numbering the pilgrim
# can reply with). Kept in sync with route_weather.ORIGIN_CITIES.
_CITY_KEYS = ["mumbai", "pune", "nashik", "kolhapur", "solapur", "sambhajinagar"]

_ASK = {
    "mr": ("🌦️ तुम्ही कुठून सुरुवात करत आहात?\n\n"
           "📍 **तुमचे स्थान शेअर करा** — खाली ➕ (जोडणी) दाबा आणि *स्थान/Location* निवडा,\n"
           "**किंवा** खालीलपैकी तुमचे शहर टाइप करा (किंवा त्याचा क्रमांक):"),
    "hi": ("🌦️ आप कहाँ से शुरू कर रहे हैं?\n\n"
           "📍 **अपना स्थान साझा करें** — नीचे ➕ (अटैचमेंट) दबाएँ और *स्थान/Location* चुनें,\n"
           "**या** नीचे से अपना शहर टाइप करें (या उसका नंबर):"),
    "en": ("🌦️ Where are you starting from?\n\n"
           "📍 **Share your location** — tap ➕ (attachment) below and choose *Location*,\n"
           "**or** reply with your starting city from the list (or its number):"),
}
_RAIN = {
    "mr": "⚠️ मार्गावर पाऊस अपेक्षित — रेनकोट/छत्री सोबत ठेवा.",
    "hi": "⚠️ मार्ग पर बारिश संभव — रेनकोट/छाता साथ रखें।",
    "en": "⚠️ Rain likely on the route — carry a raincoat/umbrella.",
}
_SOURCE = {"mr": "स्रोत: Open-Meteo · थेट", "hi": "स्रोत: Open-Meteo · लाइव", "en": "Source: Open-Meteo · live"}
_YOU = {"mr": "तुमचे स्थान", "hi": "आपका स्थान", "en": "Your location"}


def _emoji(code) -> str:
    from agent.weather_client import _bucket
    return {"clear": "☀️", "cloudy": "⛅", "rain": "🌧️", "thunder": "⛈️", "mixed": "🌦️"}[_bucket(code)]


def _city_list(lang: str) -> str:
    return "\n".join(f"{i}. {t(rw.ORIGIN_CITIES[k]['name'], lang)}" for i, k in enumerate(_CITY_KEYS, 1))


def _last_user(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


def _resolve_origin_from_text(text: str):
    """A named city, or a bare number picking from the offered list. Returns a
    city dict {name, lat, lng} or None."""
    s = (text or "").strip()
    if s.isdigit():
        i = int(s)
        if 1 <= i <= len(_CITY_KEYS):
            return rw.ORIGIN_CITIES[_CITY_KEYS[i - 1]]
    return rw.resolve_city(s)


def _ask(state: YatraState, lang: str) -> YatraState:
    body = _ASK[lang] + "\n\n" + _city_list(lang)
    return {**state, "current_node": "weather", "awaiting": "weather_origin",  # type: ignore[typeddict-item]
            "messages": (state.get("messages") or []) + [AIMessage(content=body)]}


async def _render(state: YatraState, lang: str, yatra: str, lat: float, lng: float, name: dict) -> YatraState:
    points = await rw.route_weather(lat, lng, yatra, name)
    lines = [f"{_HEADER[lang]} — {t(_YATRA_NAME.get(yatra, {}), lang)}", ""]
    for p in points:
        pin = "📍 **" + t(p["name"], lang) + "**" if p.get("you") else "📍 " + t(p["name"], lang)
        temp = f"{p['temp_c']}°C" if p.get("temp_c") is not None else "—"
        lines.append(f"{pin} — {_emoji(p.get('code'))} {temp} · {t(p['summary'], lang)}")
    if any(p.get("rain") for p in points):
        lines += ["", _RAIN[lang]]
    lines += ["", _SOURCE[lang]]
    # Origin satisfied → clear the sticky awaiting flag.
    return {**state, "current_node": "weather", "awaiting": None,  # type: ignore[typeddict-item]
            "messages": (state.get("messages") or []) + [AIMessage(content="\n".join(lines))]}


async def weather(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    # 1) A location shared natively in chat this turn.
    loc = state.get("shared_location")
    if loc and loc.get("lat") is not None and loc.get("lng") is not None:
        return await _render(state, lang, yatra, float(loc["lat"]), float(loc["lng"]), _YOU)

    # 2) A city named or picked by number.
    city = _resolve_origin_from_text(_last_user(messages))
    if city:
        return await _render(state, lang, yatra, city["lat"], city["lng"], city["name"])

    # 3) Ask — share location or pick a city, all in chat.
    return _ask(state, lang)
