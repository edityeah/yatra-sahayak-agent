"""Realtime function tools Setu can invoke mid-call.

Three tools:
  - raise_sos:      raise an emergency SOS, POSTs to the web service
  - get_weather:    current route weather for the caller's yatra
  - get_helplines:  helpline numbers for the caller's yatra

raise_sos goes through the web service via HTTP POST (X-API-Key) — NOT
direct DB access, matching the voice worker's narrow dependency surface
(OpenAI + LiveKit + AGENT_API_HOST/KEY only, no Postgres credentials in
this process). get_weather / get_helplines read local seed data /
weather_client directly — both are pure, DB-free, and safe to call from
the worker.
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
        async with httpx.AsyncClient(timeout=6.0) as c:
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
async def get_weather(context: RunContext) -> str:
    """Get the current route weather for the caller's yatra to read aloud."""
    from agent.weather_client import get_forecast
    from agent.seed import t

    md = _meta(context)
    yatra = md.get("yatra") or "pandharpur"
    f = await get_forecast(yatra)
    lang = md.get("language") or "mr"
    summary = t(f.get("summary"), lang)
    temp = f.get("temp_c")
    alert = t(f.get("rain_alert"), lang) if f.get("rain_alert") else None
    parts = [summary]
    if temp is not None:
        parts.append(f"about {temp} degrees")
    if alert:
        parts.append(f"weather alert: {alert}")
    return "Read this aloud, briefly, in the caller's language: " + "; ".join(parts)


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
        async with httpx.AsyncClient(timeout=6.0) as c:
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
        async with httpx.AsyncClient(timeout=6.0) as c:
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


ALL_TOOLS = [raise_sos, register_for_yatra, file_grievance, get_weather, get_helplines]
