"""Realtime function tools Setu can invoke mid-call — parity with the chat
agent's activities, so a voice caller can do everything a chat user can:

  - raise_sos:            emergency SOS (POSTs to the web service)
  - register_for_yatra:   yatra-pass registration (POSTs to the web service)
  - file_grievance:       lodge a complaint (POSTs to the web service)
  - report_lost_found:    report a missing person/item (POSTs; person → SOS)
  - get_weather:          destination or route weather (route if a start city given)
  - get_helplines:        emergency/helpline numbers
  - get_advisories:       official advisories (closures, diversions, weather)
  - get_transport_rates:  approved pony/palkhi/porter fares (anti-overcharge)
  - get_route_info:       named halts + day-by-day itinerary / directions

Write tools (SOS, register, grievance, lost&found) go through the web service
via HTTP POST (X-API-Key) — NOT direct DB access — keeping the worker's
dependency surface narrow (OpenAI + LiveKit + AGENT_API_HOST/KEY only, no
Postgres creds). Read tools load local seed data / weather_client directly —
pure, DB-free, safe to call from the worker.
"""
from __future__ import annotations

import json
import logging

import httpx
from livekit.agents import RunContext, function_tool, get_job_context

from agent.config import get_settings

logger = logging.getLogger(__name__)


def _meta(context: RunContext) -> dict:
    """Pull the job-dispatch metadata dict off the current job.

    RunContext (the object livekit passes into tool bodies) does not
    carry the job directly in v1.6 — fetch the current JobContext via
    the contextvar set at entrypoint time instead.
    """
    try:
        jc = get_job_context()
        raw = jc.job.metadata if jc and jc.job else None
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


@function_tool
async def raise_sos(context: RunContext, nature: str, location: str | None = None) -> str:
    """Raise an emergency SOS for the caller. Call this the moment the
    caller reports an emergency (stampede, drowning, medical, fire,
    missing person, accident).

    Args:
        context:  injected by the runtime, do not pass manually.
        nature:   a few words on what's happening (e.g. "stampede near
                  ghat", "person unconscious").
        location: where the caller is, if they said it; None if not.
    """
    md = _meta(context)
    s = get_settings()
    payload = {
        "user_id": md.get("user_id", "voice-caller"),
        "yatra": md.get("yatra"),
        "nature": nature,
        "location": location,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(
                f"{s.AGENT_API_HOST}/api/voice/sos",
                headers={"X-API-Key": s.AGENT_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            sos_id = r.json().get("sos_id")
    except Exception:
        logger.exception("raise_sos failed")
        return (
            "I could not reach the control room system. Tell the caller to call 112 "
            "IMMEDIATELY and stay where they are."
        )
    return (
        f"SOS {sos_id} has been sent to the control room. Tell the caller, calmly: the "
        "control room has been alerted, call 112 now if in danger, and stay where you are — "
        "help is coming."
    )


@function_tool
async def get_weather(context: RunContext, origin_city: str | None = None) -> str:
    """Weather for the caller's yatra, to read aloud. If the caller names the
    city they're starting from, give the weather at the halts ALONG their route
    to the destination (ask "where are you starting from?" if they haven't).

    Args:
        context:     injected by the runtime, do not pass manually.
        origin_city: the city the caller is starting from (e.g. "Pune",
                     "Mumbai", "Nashik"), or None for destination-only weather.
    """
    from agent.seed import t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"

    # Route weather from a named origin — parity with the chat weather flow.
    if origin_city:
        from agent import route_weather as rw
        city = rw.resolve_city(origin_city)
        if city:
            points = await rw.route_weather(city["lat"], city["lng"], yatra, city["name"])
            legs = []
            for p in points:
                temp = f"{p['temp_c']} degrees" if p.get("temp_c") is not None else ""
                legs.append(f"{t(p['name'], lang)}: {t(p['summary'], lang)} {temp}".strip())
            warn = " Rain is likely on the route — advise a raincoat." if any(p.get("rain") for p in points) else ""
            return ("Read this aloud, briefly, in the caller's language — weather along the route: "
                    + "; ".join(legs) + "." + warn)

    from agent.weather_client import get_forecast
    f = await get_forecast(yatra)
    summary = t(f.get("summary"), lang)
    temp = f.get("temp_c")
    alert = t(f.get("rain_alert"), lang) if f.get("rain_alert") else None
    parts = [summary]
    if temp is not None:
        parts.append(f"about {temp} degrees")
    if alert:
        parts.append(f"weather alert: {alert}")
    return ("Read this aloud, briefly, in the caller's language. If they want route weather, "
            "ask which city they're starting from: " + "; ".join(parts))


@function_tool
async def register_for_yatra(context: RunContext, name: str, age: str, phone: str,
                            yatra: str | None = None, group_name: str = "",
                            emergency_contact: str = "", medical_flags: str = "") -> str:
    """Register the caller for a yatra pass. FIRST collect, by voice, one at a
    time: their full name, age, 10-digit mobile number, which yatra (Pandharpur
    Wari or Simhastha Kumbh), their Dindi/group if any, an emergency contact
    (name + number), and any medical conditions. THEN call this to issue the
    pass and read back the Yatra ID.

    Args:
        context: injected by the runtime, do not pass manually.
        name:    the caller's full name.
        age:     age in years.
        phone:   10-digit mobile number.
        yatra:   "pandharpur" or "kumbh"; None to use the call's yatra.
        group_name:        Dindi/group name, or "".
        emergency_contact: an emergency contact name + number, or "".
        medical_flags:     medical conditions to note, or "".
    """
    md = _meta(context)
    s = get_settings()
    payload = {
        "user_id": md.get("user_id", "voice-caller"),
        "yatra": (yatra or md.get("yatra") or "pandharpur"),
        "name": name, "age": age, "phone": phone, "group_name": group_name,
        "emergency_contact": emergency_contact, "medical_flags": medical_flags,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(
                f"{s.AGENT_API_HOST}/api/register",
                headers={"X-API-Key": s.AGENT_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            yatra_id = r.json().get("yatra_id")
    except Exception:
        logger.exception("register_for_yatra failed")
        return "I couldn't reach the registration system. Ask the caller to try again in a moment."
    return (
        f"Registration complete. Read the Yatra ID aloud slowly, digit by digit: {yatra_id}. "
        "Tell the caller their QR yatra pass is now ready and can be shown at checkpoints."
    )


@function_tool
async def file_grievance(context: RunContext, category: str, description: str,
                         location: str | None = None) -> str:
    """File a grievance/complaint on the caller's behalf (overcharging, poor or
    absent facilities, cleanliness, safety, or staff conduct). Collect the
    category and what happened, then call this. Reads back a reference number.

    Args:
        context:     injected by the runtime, do not pass manually.
        category:    one of overcharging / facilities / cleanliness / safety /
                     staff / other.
        description: what happened, in a sentence.
        location:    where it happened, if the caller said it; else None.
    """
    md = _meta(context)
    s = get_settings()
    payload = {
        "yatra": md.get("yatra"), "category": category, "description": description,
        "location": location or "", "reporter_phone": md.get("phone", ""),
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(
                f"{s.AGENT_API_HOST}/api/grievances",
                headers={"X-API-Key": s.AGENT_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            gid = r.json().get("id")
    except Exception:
        logger.exception("file_grievance failed")
        return "I couldn't reach the control room. Ask the caller to try again shortly."
    return (
        f"Grievance {gid} has been filed with the control room. Read the reference number "
        "aloud, and tell the caller officers will look into it."
    )


@function_tool
async def get_helplines(context: RunContext) -> str:
    """Get the emergency/helpline numbers for the caller's yatra to read aloud."""
    from agent.seed import load, t

    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    entries = load("helplines").get(yatra, [])
    lines = [f"{t(e['label'], lang)}: {e['number']}" for e in entries]
    return "Read these numbers slowly, one at a time, in the caller's language: " + "; ".join(lines)


@function_tool
async def get_advisories(context: RunContext) -> str:
    """Get the current official advisories (road closures, diversions, weather,
    schedule changes) for the caller's yatra, to read aloud."""
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    items = load("advisories").get(yatra, [])
    if not items:
        return "Tell the caller there are no active advisories right now."
    lines = [f"{t(a.get('title'), lang)} — {t(a.get('body'), lang)}" for a in items[:4]]
    return "Read these advisories aloud, briefly, in the caller's language: " + "; ".join(lines)


@function_tool
async def get_alerts(context: RunContext) -> str:
    """Get the active emergency alerts the control room / State Emergency Control
    Centre has broadcast for the caller's yatra, to read aloud. Use when the
    caller asks 'any alerts?', 'is it safe?', 'any warnings', or about a current
    situation (crowd, weather, closure) affecting the yatra right now."""
    from agent import persistence

    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    alerts = await persistence.list_alerts(yatra, active_only=True)
    if not alerts:
        return "Tell the caller there are no active alerts right now, and to stay with their group."
    # Most severe first so the caller hears the critical ones first.
    order = {"critical": 0, "danger": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: order.get((a.get("severity") or "info").lower(), 2))
    lines = []
    for a in alerts[:4]:
        sev = (a.get("severity") or "info").lower()
        tag = "URGENT — " if sev in ("critical", "danger") else ""
        lines.append(f"{tag}{a.get('title') or ''}: {a.get('message') or ''}".strip())
    return ("Read these official control-room alerts aloud in the caller's language, urgent ones "
            "first, calmly and clearly: " + " | ".join(lines))


@function_tool
async def get_darshan(context: RunContext) -> str:
    """Get temple darshan / aarti / puja timings (and for the Kumbh, the
    shahi-snan / parvani bathing info and which ghat) for the caller's yatra, to
    read aloud. Use for 'darshan timings', 'aarti', 'when is the snan', 'which
    ghat', 'temple hours'."""
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    data = load("darshan").get(yatra)
    if not data:
        return "Tell the caller darshan details aren't listed yet; suggest asking a marshal."
    parts = [f"{t(i.get('label'), lang)}: {t(i.get('value'), lang)}" for i in data.get("items", [])]
    return ("Read this darshan/snan info aloud, in the caller's language, clearly: "
            + t(data.get("title"), lang) + " — " + "; ".join(parts))


@function_tool
async def get_accommodation(context: RunContext) -> str:
    """Get where to stay and the per-night tariffs (Bhakta Niwas, tents, dindi
    camps, dharamshalas) for the caller's yatra, to read aloud. Use for 'where
    to stay', 'lodging', 'room', 'tent', 'tariff', 'accommodation'."""
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    entries = load("accommodation").get(yatra, [])
    if not entries:
        return "Tell the caller accommodation details aren't listed yet."
    lines = [f"{t(e['name'], lang)} ({t(e.get('type'), lang)}): {e.get('tariff','')}" for e in entries[:5]]
    return "Read these stay options and tariffs aloud, in the caller's language: " + "; ".join(lines)


@function_tool
async def get_langar(context: RunContext) -> str:
    """Get the free-food / langar / annadan / bhandara locations along the
    caller's route, to read aloud. Use for 'free food', 'langar', 'annadan',
    'bhandara', 'where can I eat'."""
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    entries = load("langar").get(yatra, [])
    if not entries:
        return "Tell the caller free-food points aren't listed yet."
    lines = [f"{t(e['name'], lang)} — {t(e.get('location'), lang)}" for e in entries[:6]]
    return "Read these free-food / langar points aloud, in the caller's language: " + "; ".join(lines)


@function_tool
async def get_palkhi(context: RunContext) -> str:
    """Get palkhi tracking info and the Wari schedule to read aloud: the official
    live-tracking website, the key dates, and — if asked — nodal-officer contact
    numbers. Use for 'where is the palkhi', 'track the palkhi', 'wari dates', or
    'nodal officer number'."""
    from agent.seed import load, t
    md = _meta(context)
    lang = md.get("language") or "mr"
    data = load("palkhis")
    meta = data.get("meta", {})
    sched = meta.get("schedule", {})
    parts = [f"Live palkhi tracking during the yatra is on the Solapur police website "
             f"{meta.get('tracker_url','')}."]
    for k in ("period", "main_days", "entries"):
        if sched.get(k):
            parts.append(t(sched[k], lang))
    return ("Read this palkhi/schedule info aloud, in the caller's language, and spell the "
            "website slowly: " + " ".join(parts))


@function_tool
async def get_parking(context: RunContext) -> str:
    """Get the names of the designated vehicle parking areas for the yatra town,
    to read aloud. Use for 'where to park', 'parking'. Tell the caller to use the
    app for turn-by-turn navigation to each lot."""
    from agent.seed import load
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lots = load("parking").get(yatra, [])
    if not lots:
        return "Tell the caller parking details aren't listed yet."
    names = [l["name"] for l in lots[:8]]
    return ("Read these parking areas aloud, in the caller's language, and say they can open the "
            "app for GPS navigation to any of them: " + "; ".join(names))


@function_tool
async def get_facilities(context: RunContext, kind: str = "medical") -> str:
    """List route facilities of a given kind for the caller's yatra, to read
    aloud. Use for 'where are the medical posts / toilets / drinking water /
    bathing ghats'.

    Args:
        context: injected by the runtime, do not pass manually.
        kind:    one of 'medical', 'water', 'toilet', 'ghat'.
    """
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    kind = (kind or "medical").lower()
    if kind not in ("medical", "water", "toilet", "ghat"):
        kind = "medical"
    pois = [p for p in load("routes").get(yatra, []) if p.get("kind") == kind]
    if not pois:
        return f"Tell the caller no {kind} facilities are mapped for this route yet."
    names = [t(p.get("name"), lang) for p in pois[:8]]
    return (f"Read these {kind} facilities aloud, in the caller's language, and suggest they use "
            f"the app to find the nearest one by location: " + "; ".join(names))


@function_tool
async def get_transport_rates(context: RunContext) -> str:
    """Get approved transport / porter rates (bullock cart, pony, palkhi porter,
    etc.) for the caller's yatra, to read aloud. Use when the caller asks about
    fares, rates, or thinks they're being overcharged."""
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    rates = load("logistics_rates").get(yatra, [])
    if not rates:
        return "Tell the caller official rates aren't listed for this yatra; suggest asking a marshal."
    lines = [f"{t(r.get('service'), lang)}: {r.get('rate','')} {t(r.get('unit'), lang)}".strip() for r in rates[:6]]
    return ("Read these approved rates aloud, in the caller's language, and note they're official "
            "estimates so they can refuse overcharging: " + "; ".join(lines))


@function_tool
async def get_route_info(context: RunContext, day: int | None = None) -> str:
    """Get route guidance for the caller's yatra — the named halts along the way
    and the day-by-day itinerary. Use for directions, "which way", "what's the
    route", or planning a stage. Optionally pass a day number for that day's leg.

    Args:
        context: injected by the runtime, do not pass manually.
        day:     an itinerary day number to detail, or None for an overview.
    """
    from agent.seed import load, t
    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    lang = md.get("language") or "mr"
    itinerary = load("itinerary").get(yatra, [])
    if day is not None:
        leg = next((d for d in itinerary if d.get("day") == day), None)
        if leg:
            return (f"Read aloud, in the caller's language — day {day}: {t(leg.get('title'), lang)}, "
                    f"about {leg.get('distance_km','')} kilometres. {t(leg.get('note'), lang)}")
    halts = [t(h.get("name"), lang) for h in load("routes").get(yatra, []) if h.get("name")]
    overview = ("Read aloud, briefly, in the caller's language. Main halts on the route: "
                + ", ".join(halts[:8]) + f". The journey is {len(itinerary)} days.")
    if itinerary:
        d1 = itinerary[0]
        overview += f" Day 1 is {t(d1.get('title'), lang)}, about {d1.get('distance_km','')} kilometres."
    overview += " Offer to detail any specific day."
    return overview


@function_tool
async def report_lost_found(context: RunContext, kind: str, name: str,
                            description: str = "", last_seen: str = "") -> str:
    """File a lost-and-found report on the caller's behalf. A missing PERSON is
    treated as an emergency and also alerts the control room.

    Args:
        context:     injected by the runtime, do not pass manually.
        kind:        "person" for a missing person, or "item" for a lost belonging.
        name:        the missing person's name, or a short name for the item.
        description: distinguishing details (clothing, colour, contents), if given.
        last_seen:   where/when they were last seen, if the caller said it.
    """
    md = _meta(context)
    s = get_settings()
    payload = {
        "kind": ("person" if str(kind).lower().startswith("p") else "item"),
        "name": name, "description": description, "last_seen": last_seen,
        "reporter_phone": md.get("phone", md.get("user_id", "")), "yatra": md.get("yatra"),
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(
                f"{s.AGENT_API_HOST}/api/lostfound",
                headers={"X-API-Key": s.AGENT_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            lid = r.json().get("id")
    except Exception:
        logger.exception("report_lost_found failed")
        return "I couldn't reach the lost-and-found desk. Ask the caller to try again shortly."
    if payload["kind"] == "person":
        return (f"Report {lid} filed and the control room has been alerted about the missing person. "
                "Reassure the caller that officers are now looking, and to stay where they are.")
    return (f"Lost-item report {lid} has been filed. Tell the caller to check the nearest lost-and-found "
            "desk and that officers will reach out if it's found.")


ALL_TOOLS = [
    raise_sos, register_for_yatra, file_grievance, get_weather, get_helplines,
    get_advisories, get_alerts, get_transport_rates, get_route_info, report_lost_found,
    get_darshan, get_accommodation, get_langar, get_facilities,
    get_palkhi, get_parking,
]
