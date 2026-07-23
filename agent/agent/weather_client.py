"""IMD weather client — best-effort live call with a cached fallback.

get_forecast(yatra) returns a dict:
  {"summary": <trilingual dict>, "temp_c": int, "rain_alert": <trilingual dict|None>, "source": "live"|"cached"}
Live is attempted only when settings.IMD_API_URL is set; ANY error (no URL,
timeout, bad status, unexpected shape) falls back to data/weather_fallback.json.
The live-response field mapping is a placeholder — wire it to the real IMD
schema when a live endpoint is available."""
from __future__ import annotations
import httpx

from agent.config import get_settings
from agent.seed import load


def _cached(yatra: str) -> dict:
    fb = load("weather_fallback").get(yatra) or {}
    return {
        "summary": fb.get("summary", {"en": "Forecast unavailable."}),
        "temp_c": fb.get("temp_c"),
        "rain_alert": fb.get("rain_alert"),
        "source": "cached",
    }


async def get_forecast(yatra: str) -> dict:
    url = get_settings().IMD_API_URL
    if not url:
        return _cached(yatra)
    try:
        target = url.replace("{yatra}", yatra)
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(target)
            resp.raise_for_status()
            data = resp.json()
        # Placeholder mapping — adapt to the real IMD schema when wired.
        return {
            "summary": {"en": str(data.get("summary") or data.get("description") or "")},
            "temp_c": data.get("temp_c") or data.get("temp"),
            "rain_alert": ({"en": str(data.get("rain_alert"))} if data.get("rain_alert") else None),
            "source": "live",
        }
    except Exception as e:
        print(f"[weather] live IMD call failed ({e!r}); using cached fallback", flush=True)
        return _cached(yatra)
