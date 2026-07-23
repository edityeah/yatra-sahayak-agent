"""Weather client — live forecast with a cached fallback.

get_forecast(yatra) returns:
  {"summary": <trilingual dict>, "temp_c": int|None, "rain_alert": <trilingual dict|None>, "source": "live"|"cached"}

Live path: if settings.IMD_API_URL is set, call it (placeholder mapping — adapt
to IMD's real schema once onboarded); otherwise call **Open-Meteo** (free, no
API key) using the yatra's coordinates. ANY error → data/weather_fallback.json.
"""
from __future__ import annotations
import httpx

from agent.config import get_settings
from agent.seed import load

# Representative coordinates per yatra (Pandharpur = Vitthal temple;
# Kumbh = Nashik / Ramkund).
_COORDS = {
    "pandharpur": (17.679, 75.333),
    "kumbh": (19.995, 73.790),
}

# WMO weather_code buckets → trilingual summary.
_WMO = {
    "clear":   {"mr": "निरभ्र आकाश", "hi": "साफ़ आसमान", "en": "Clear skies"},
    "cloudy":  {"mr": "ढगाळ वातावरण", "hi": "बादल छाए रहेंगे", "en": "Cloudy"},
    "rain":    {"mr": "पावसाची शक्यता", "hi": "बारिश की संभावना", "en": "Rain likely"},
    "thunder": {"mr": "वादळी पाऊस", "hi": "आंधी-तूफान", "en": "Thunderstorms"},
    "mixed":   {"mr": "मिश्र हवामान", "hi": "मिश्रित मौसम", "en": "Mixed conditions"},
}
_RAIN_ALERT = {
    "mr": "पावसाचा इशारा — सोबत रेनकोट/छत्री ठेवा",
    "hi": "बारिश की चेतावनी — रेनकोट/छाता साथ रखें",
    "en": "Rain likely — carry a raincoat/umbrella",
}


def _bucket(code) -> str:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "mixed"
    if c in (0, 1):
        return "clear"
    if c in (2, 3, 45, 48):
        return "cloudy"
    if 95 <= c <= 99:
        return "thunder"
    if (51 <= c <= 67) or (80 <= c <= 86):
        return "rain"
    return "mixed"


def _cached(yatra: str) -> dict:
    fb = load("weather_fallback").get(yatra) or {}
    return {
        "summary": fb.get("summary", {"en": "Forecast unavailable."}),
        "temp_c": fb.get("temp_c"),
        "rain_alert": fb.get("rain_alert"),
        "source": "cached",
    }


async def _open_meteo(yatra: str) -> dict:
    lat, lon = _COORDS.get(yatra, _COORDS["pandharpur"])
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code"
        "&daily=precipitation_probability_max&timezone=auto&forecast_days=1"
    )
    async with httpx.AsyncClient(timeout=6.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    cur = data.get("current") or {}
    temp = cur.get("temperature_2m")
    daily = data.get("daily") or {}
    probs = daily.get("precipitation_probability_max") or []
    rainy = bool(probs) and isinstance(probs[0], (int, float)) and probs[0] >= 50
    return {
        "summary": _WMO[_bucket(cur.get("weather_code"))],
        "temp_c": round(temp) if isinstance(temp, (int, float)) else None,
        "rain_alert": _RAIN_ALERT if rainy else None,
        "source": "live",
    }


async def get_forecast(yatra: str) -> dict:
    settings = get_settings()
    try:
        if settings.IMD_API_URL:
            target = settings.IMD_API_URL.replace("{yatra}", yatra)
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(target)
                resp.raise_for_status()
                data = resp.json()
            # Placeholder mapping — adapt to IMD's real schema when wired.
            return {
                "summary": {"en": str(data.get("summary") or data.get("description") or "")},
                "temp_c": data.get("temp_c") or data.get("temp"),
                "rain_alert": ({"en": str(data.get("rain_alert"))} if data.get("rain_alert") else None),
                "source": "live",
            }
        return await _open_meteo(yatra)
    except Exception as e:
        print(f"[weather] live call failed ({e!r}); using cached fallback", flush=True)
        return _cached(yatra)
