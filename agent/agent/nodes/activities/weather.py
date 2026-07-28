"""weather activity — route weather from the caller's origin to the yatra
destination. If no origin is given, ask for it with tappable location chips;
if a known city is named, render live weather at the named halts along the route.
"""
from __future__ import annotations
from langchain_core.messages import AIMessage, HumanMessage
from agent.state import YatraState
from agent.config import get_settings
from agent.seed import t
from agent import route_weather as rw

_YATRA_NAME = {
    "pandharpur": {"mr": "पंढरपूर वारी", "hi": "पंढरपुर वारी", "en": "Pandharpur Wari"},
    "kumbh": {"mr": "सिंहस्थ कुंभ", "hi": "सिंहस्थ कुंभ", "en": "Simhastha Kumbh"},
}
_HEADER = {"mr": "🌦️ **तुमच्या मार्गावरील हवामान**", "hi": "🌦️ **आपके मार्ग का मौसम**", "en": "🌦️ **Weather on your route**"}
_ASK = {
    "mr": "🌦️ तुम्ही कुठून सुरुवात करत आहात? खालील शहर निवडा, किंवा [📍 थेट स्थान शेअर करा]({url}).",
    "hi": "🌦️ आप कहाँ से शुरू कर रहे हैं? नीचे शहर चुनें, या [📍 लाइव स्थान साझा करें]({url}).",
    "en": "🌦️ Where are you starting from? Tap a city below, or [📍 share your live location]({url}).",
}
_RAIN = {
    "mr": "⚠️ मार्गावर पाऊस अपेक्षित — रेनकोट/छत्री सोबत ठेवा.",
    "hi": "⚠️ मार्ग पर बारिश संभव — रेनकोट/छाता साथ रखें।",
    "en": "⚠️ Rain likely on the route — carry a raincoat/umbrella.",
}
_SOURCE = {"mr": "स्रोत: Open-Meteo · थेट", "hi": "स्रोत: Open-Meteo · लाइव", "en": "Source: Open-Meteo · live"}

# Origin cities offered as chips (value re-asks weather so the router re-routes).
_CHIP_CITIES = [("mumbai", "Mumbai"), ("pune", "Pune"), ("nashik", "Nashik"), ("sambhajinagar", "Sambhajinagar")]


def _emoji(code) -> str:
    from agent.weather_client import _bucket
    return {"clear": "☀️", "cloudy": "⛅", "rain": "🌧️", "thunder": "⛈️", "mixed": "🌦️"}[_bucket(code)]


def _choices(lang: str) -> str:
    parts = []
    for key, en in _CHIP_CITIES:
        label = t(rw.ORIGIN_CITIES[key]["name"], lang)
        parts.append(f"{label}::weather from {en}")
    return "[[choices:" + "||".join(parts) + "]]"


def _last_user(messages) -> str:
    for m in reversed(messages or []):
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


async def weather(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"
    settings = get_settings()

    city = rw.resolve_city(_last_user(messages))
    if not city:
        url = f"{settings.PUBLIC_WEBVIEW_BASE}/yatri/weather?yatra={yatra}&lang={lang}"
        body = _ASK[lang].format(url=url) + "\n\n" + _choices(lang)
        return {**state, "current_node": "weather", "messages": messages + [AIMessage(content=body)]}

    points = await rw.route_weather(city["lat"], city["lng"], yatra, city["name"])
    lines = [f"{_HEADER[lang]} — {t(_YATRA_NAME.get(yatra, {}), lang)}", ""]
    for p in points:
        pin = "📍 **" + t(p["name"], lang) + "**" if p.get("you") else "📍 " + t(p["name"], lang)
        temp = f"{p['temp_c']}°C" if p.get("temp_c") is not None else "—"
        lines.append(f"{pin} — {_emoji(p.get('code'))} {temp} · {t(p['summary'], lang)}")
    if any(p.get("rain") for p in points):
        lines += ["", _RAIN[lang]]
    lines += ["", _SOURCE[lang]]
    return {**state, "current_node": "weather", "messages": messages + [AIMessage(content="\n".join(lines))]}
