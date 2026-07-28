"""Route weather — weather at the real named halts along a yatra route.

Given an origin (lat/lng, or a known city name), find the nearest halt in
routes.json, slice the halts from there to the destination, and fetch live
weather at each point (origin + halts) via weather_client. Shared by the
/api/route-weather endpoint (web) and the chat weather node.
"""
from __future__ import annotations
import math

import httpx

from agent.seed import load
from agent import weather_client

# Reverse-geocode a shared pin to a human place name so the route card says
# WHERE the pilgrim is ("Kothrud, Pune") instead of a generic "Your location".
# OpenStreetMap Nominatim: free, no key. Never raises — falls back to the
# generic label so a geocoder hiccup never breaks the weather reply.
_NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
_YOU_FALLBACK = {"mr": "तुमचे स्थान", "hi": "आपका स्थान", "en": "Your location"}


async def reverse_geocode(lat: float, lng: float) -> dict:
    """Return a {mr,hi,en} place-name dict for a coordinate. A place name is a
    proper noun, so the same string is used across languages. Falls back to the
    trilingual 'Your location' label on any failure."""
    try:
        params = {"lat": lat, "lon": lng, "format": "jsonv2", "zoom": "14", "addressdetails": "1"}
        headers = {"User-Agent": "maharashtra-yatra-sahayak/1.0 (pilgrim-safety)"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(_NOMINATIM, params=params, headers=headers)
            resp.raise_for_status()
            addr = (resp.json() or {}).get("address") or {}
        # Prefer a "locality, city" style; fall back through the admin levels.
        locality = addr.get("suburb") or addr.get("neighbourhood") or addr.get("village") or addr.get("town")
        city = addr.get("city") or addr.get("town") or addr.get("county") or addr.get("state_district")
        parts = [p for p in (locality, city) if p]
        # De-dupe when locality == city; keep it short (max two parts).
        seen, name_parts = set(), []
        for p in parts:
            if p not in seen:
                seen.add(p)
                name_parts.append(p)
        name = ", ".join(name_parts[:2]) or addr.get("state") or ""
        if not name:
            return dict(_YOU_FALLBACK)
        return {"mr": name, "hi": name, "en": name}
    except Exception:
        return dict(_YOU_FALLBACK)

# Destination (final point) per yatra.
_DEST = {
    "pandharpur": {"name": {"mr": "पंढरपूर", "hi": "पंढरपुर", "en": "Pandharpur"}, "lat": 17.679, "lng": 75.333},
    "kumbh": {"name": {"mr": "रामकुंड, नाशिक", "hi": "रामकुंड, नासिक", "en": "Ramkund, Nashik"}, "lat": 20.007, "lng": 73.792},
}
# Which routes.json kinds count as route stops for each yatra.
_STOP_KINDS = {"pandharpur": ("night_halt",), "kumbh": ("ghat",)}

# Known origin cities (for the chat city chips + resolving typed names).
ORIGIN_CITIES = {
    "mumbai": {"name": {"mr": "मुंबई", "hi": "मुंबई", "en": "Mumbai"}, "lat": 19.076, "lng": 72.877},
    "pune": {"name": {"mr": "पुणे", "hi": "पुणे", "en": "Pune"}, "lat": 18.516, "lng": 73.856},
    "nashik": {"name": {"mr": "नाशिक", "hi": "नासिक", "en": "Nashik"}, "lat": 19.997, "lng": 73.790},
    "kolhapur": {"name": {"mr": "कोल्हापूर", "hi": "कोल्हापुर", "en": "Kolhapur"}, "lat": 16.705, "lng": 74.243},
    "solapur": {"name": {"mr": "सोलापूर", "hi": "सोलापुर", "en": "Solapur"}, "lat": 17.659, "lng": 75.906},
    "sambhajinagar": {"name": {"mr": "छत्रपती संभाजीनगर", "hi": "छत्रपति संभाजीनगर", "en": "Chh. Sambhajinagar"}, "lat": 19.876, "lng": 75.343},
    "nagpur": {"name": {"mr": "नागपूर", "hi": "नागपुर", "en": "Nagpur"}, "lat": 21.146, "lng": 79.088},
}
_CITY_ALIASES = {"aurangabad": "sambhajinagar", "mumba": "mumbai"}

_MAX_POINTS = 6


def _hav(a: dict, b: dict) -> float:
    R = 6371.0
    dlat = math.radians(b["lat"] - a["lat"])
    dlng = math.radians(b["lng"] - a["lng"])
    s = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a["lat"])) * math.cos(math.radians(b["lat"])) * math.sin(dlng / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(s))


def route_stops(yatra: str) -> list[dict]:
    """Ordered named halts (start → destination) from routes.json + the destination."""
    dest = _DEST.get(yatra, _DEST["pandharpur"])
    kinds = _STOP_KINDS.get(yatra, ("night_halt",))
    rows = load("routes").get(yatra, []) or []
    stops = [{"name": r["name"], "lat": r["lat"], "lng": r["lng"]}
             for r in rows if r.get("kind") in kinds
             and isinstance(r.get("lat"), (int, float)) and isinstance(r.get("lng"), (int, float))]
    # Order start → destination by distance-to-destination (farthest first).
    stops.sort(key=lambda s: _hav(s, dest), reverse=True)
    stops.append({"name": dest["name"], "lat": dest["lat"], "lng": dest["lng"]})
    return stops


def resolve_city(text: str) -> dict | None:
    t = (text or "").strip().lower()
    for alias, real in _CITY_ALIASES.items():
        if alias in t:
            return ORIGIN_CITIES[real]
    for key, city in ORIGIN_CITIES.items():
        if key in t:
            return city
    return None


async def route_weather(origin_lat: float, origin_lng: float, yatra: str,
                        origin_name: dict | None = None) -> list[dict]:
    """Origin + the halts from the nearest one to the destination, each with live
    weather. Returns a list of {name, you, lat, lng, temp_c, code, summary, rain}."""
    origin = {"lat": origin_lat, "lng": origin_lng}
    stops = route_stops(yatra)
    k = min(range(len(stops)), key=lambda i: _hav(origin, stops[i]))
    tail = stops[k:]
    pts = [{"name": origin_name or {"mr": "तुमचे ठिकाण", "hi": "आपका स्थान", "en": "You are here"},
            "lat": origin_lat, "lng": origin_lng, "you": True}]
    pts += [{**s, "you": False} for s in tail]
    # Cap the number of Open-Meteo calls: keep origin + destination, sample middle.
    if len(pts) > _MAX_POINTS:
        head, dest = pts[0], pts[-1]
        mid = pts[1:-1]
        step = max(1, len(mid) // (_MAX_POINTS - 2))
        pts = [head] + mid[::step][: _MAX_POINTS - 2] + [dest]
    wx = await weather_client.get_forecasts([(p["lat"], p["lng"]) for p in pts])
    return [{"name": p["name"], "you": p.get("you", False), "lat": p["lat"], "lng": p["lng"],
             "temp_c": w.get("temp_c"), "code": w.get("code"), "summary": w.get("summary"),
             "rain": w.get("rain", False)}
            for p, w in zip(pts, wx)]
