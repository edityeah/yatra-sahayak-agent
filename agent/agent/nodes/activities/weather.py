"""weather activity — IMD forecast, live-with-cached-fallback (Plan 2 Task 10)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState
from agent.seed import t
from agent import weather_client

_HEADER = {
    "mr": "🌦️ **हवामान अंदाज**",
    "hi": "🌦️ **मौसम पूर्वानुमान**",
    "en": "🌦️ **Weather forecast**",
}

_TEMP_LABEL = {
    "mr": "तापमान",
    "hi": "तापमान",
    "en": "Temperature",
}

_SOURCE_LABEL = {
    "live": {
        "mr": "स्रोत: थेट हवामान अद्यतन",
        "hi": "स्रोत: लाइव मौसम अपडेट",
        "en": "Source: live weather update",
    },
    "cached": {
        "mr": "स्रोत: कॅश केलेली माहिती — शेवटचे ज्ञात अद्ययावत (थेट सेवा अनुपलब्ध)",
        "hi": "स्रोत: कैश की गई जानकारी — अंतिम ज्ञात अपडेट (लाइव सेवा अनुपलब्ध)",
        "en": "Source: cached — last known update (live service unavailable)",
    },
}


async def weather(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    forecast = await weather_client.get_forecast(yatra)

    lines = [_HEADER[lang], ""]
    lines.append(t(forecast["summary"], lang))
    lines.append("")

    if forecast.get("temp_c") is not None:
        lines.append(f"🌡️ {_TEMP_LABEL[lang]}: {forecast['temp_c']} °C")

    if forecast.get("rain_alert"):
        lines.append(f"⚠️ {t(forecast['rain_alert'], lang)}")

    lines.append("")
    lines.append(_SOURCE_LABEL[forecast.get("source", "cached")][lang])

    return {
        **state,
        "current_node": "weather",
        "messages": messages + [AIMessage(content="\n".join(lines).rstrip())],
    }
