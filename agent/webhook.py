"""FastAPI webhook — entrypoint the SwiftChat platform (or curl) hits.

SSE contract (added in Task 8) mirrors swift-learning-agent/agent/webhook.py:
  event: meta    data: {"stream_id": "..."}
  event: message data: {"message": {"content": [{"type":"text","text":{"value":""}}]}}
  event: delta   data: {"p":"/message/content/0/text/value","o":"append","v":"..."}
  event: end     data: {}
  event: done    data: [DONE]
"""
from __future__ import annotations
import csv
import io
import json
import re
import uuid
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage

from agent.config import get_settings
from agent.state import new_state
from agent.graph import yatra_graph
from agent import db
from agent import session_store
from agent import persistence
from agent import seed

load_dotenv()
settings = get_settings()

app = FastAPI(title="Yatra Sahayak Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    await db.run_migrations()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "yatra-sahayak-agent", "db": settings.DB_ENABLED}


def _require_key(x_api_key: str | None) -> None:
    if x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="bad api key")


def _require_admin(x_api_key: str | None) -> None:
    """Guards pilgrim-PII endpoints. Uses ADMIN_API_KEY, which is distinct from
    the browser-shipped INTERNAL_API_KEY."""
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="admin key required")


# Columns exported by the registrations CSV, in order.
_REG_EXPORT_COLS = [
    "yatra_id", "yatra", "name", "age", "phone", "id_type", "group_name",
    "group_size", "emergency_contact", "medical_flags", "mobile_verified",
    "ekyc_verified", "created_at",
]


@app.get("/api/registrations")
async def api_registrations(format: str = "json", x_api_key: str | None = Header(default=None)):
    """Officer/admin export of all pilgrim registrations. ADMIN_API_KEY-gated.
    `?format=csv` returns a CSV download; default is JSON with a headcount."""
    _require_admin(x_api_key)
    regs = await persistence.list_registrations()

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_REG_EXPORT_COLS, extrasaction="ignore")
        writer.writeheader()
        for r in regs:
            writer.writerow({k: r.get(k, "") for k in _REG_EXPORT_COLS})
        return PlainTextResponse(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=registrations.csv"},
        )

    # Each person is now their own row (DigiYatra per-member model), so the
    # pilgrim headcount is simply the row count — never sum group_size (that's
    # a denormalized family-batch size, and summing it double-counts families).
    by_yatra: dict[str, int] = {}
    families = set()
    for r in regs:
        by_yatra[r.get("yatra", "unknown")] = by_yatra.get(r.get("yatra", "unknown"), 0) + 1
        if r.get("group_id"):
            families.add(r["group_id"])
    return {
        "count": len(regs),          # total pilgrims (one row per person)
        "families": len(families),   # distinct multi-member family batches
        "by_yatra": by_yatra,
        "registrations": regs,
    }


@app.get("/api/drills")
async def api_drills(x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    return seed.load("drills")


@app.get("/api/yatra/{yatra}")
async def api_yatra(yatra: str, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    data = seed.load("yatras").get(yatra)
    if not data:
        raise HTTPException(status_code=404, detail="unknown yatra")
    return data


@app.get("/api/yatra/{yatra}/{kind}")
async def api_yatra_kind(yatra: str, kind: str, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    file_of = {"routes": "routes", "logistics": "logistics_rates", "advisories": "advisories",
               "events": "events", "itinerary": "itinerary"}
    name = file_of.get(kind)
    if not name:
        raise HTTPException(status_code=404, detail="unknown kind")
    data = seed.load(name).get(yatra)
    if data is None:
        raise HTTPException(status_code=404, detail="unknown yatra")
    return data


@app.get("/api/pass/{yatra_id}")
async def api_pass(yatra_id: str, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    reg = await persistence.get_registration_by_id(yatra_id)
    if not reg:
        raise HTTPException(status_code=404, detail="pass not found")
    return reg


@app.get("/api/passes")
async def api_passes(user_id: str, x_api_key: str | None = Header(default=None)):
    """The yatri's wallet — every pass registered from this device/account."""
    _require_key(x_api_key)
    return await persistence.list_registrations_for_user(user_id)


_MARKER_RE = re.compile(r"\[(?:lang:(?:mr|hi|en)|yatra:(?:pandharpur|kumbh)|yatra-ask)\]")


def _clean(text: str) -> str:
    """Strip internal state markers before showing text to the user."""
    return _MARKER_RE.sub("", text or "").strip()


_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")


def _reply_language(text: str, selected: str | None) -> str | None:
    """Detect the language the user WROTE in from script: Latin → English;
    Devanagari → the user's selected mr/hi (mr vs hi can't be told from script
    alone, so use `selected`, default mr). Returns None for ambiguous input
    (digits, punctuation, "1", a bare phone number) so the caller can keep the
    conversation's existing (sticky) language instead of resetting it."""
    t = text or ""
    has_dev = bool(_DEVANAGARI_RE.search(t))
    has_latin = bool(re.search(r"[A-Za-z]", t))
    if has_latin and not has_dev:
        return "en"
    if has_dev and not has_latin:
        return selected if selected in ("mr", "hi") else "mr"
    return None  # ambiguous — no script signal this turn


def _extract_user_text(message: dict) -> str:
    for block in message.get("content", []):
        if block.get("type") == "text":
            return block.get("text", {}).get("value", "") or ""
    return ""


def _rebuild_messages(history: list[dict], user_text: str) -> list:
    """Rebuild LangChain messages from SwiftChat's prior-turn history plus
    the new user turn. history items: {role, text}. For the POC the caller
    may send an empty history and rely on per-turn statelessness."""
    msgs = []
    for h in history or []:
        role, text = h.get("role"), h.get("text", "")
        if not text:
            continue
        msgs.append(AIMessage(content=text) if role == "assistant" else HumanMessage(content=text))
    msgs.append(HumanMessage(content=user_text))
    return msgs


async def _stream_turn(body: dict) -> AsyncIterator[dict]:
    user_id = body.get("user_id", "anon")
    conv_id = body.get("conversation_id", "conv")
    user_text = _extract_user_text(body.get("message", {}))
    history = body.get("history", [])

    state = new_state(session_id=conv_id, user_id=user_id)
    state["context_from_webview"] = body.get("context_from_webview")

    # Restore this conversation's transcript from the in-process session
    # store. SwiftChat's webhook doesn't resend prior turns and markers are
    # stripped before streaming, so this store is the POC stand-in for the
    # reference's DB-backed history.
    sess = session_store.load(conv_id)
    prior = sess.get("messages")
    if prior is not None:
        state["messages"] = list(prior) + [HumanMessage(content=user_text)]
    else:
        # First turn in this process — seed from any client-sent history.
        state["messages"] = _rebuild_messages(history, user_text)

    # Registration intake is CONVERSATION-scoped (session store) so a new chat
    # never inherits a stale intake. Language + yatra are USER-scoped and live
    # in the persistence layer (DB when enabled, memory otherwise).
    if sess.get("reg_stage"):
        state["reg_stage"] = sess["reg_stage"]
    if sess.get("reg_fields"):
        state["reg_fields"] = sess["reg_fields"]
    ustate = await persistence.get_user_state(user_id)
    if ustate.get("active_yatra"):
        state["active_yatra"] = ustate["active_yatra"]

    # The webview sends a `yatra` hint (header) so the agent skips the yatra ask.
    if body.get("yatra") in ("pandharpur", "kumbh"):
        state["active_yatra"] = body["yatra"]

    # Language: reply in the language the user actually WROTE in (typed English
    # → English). For a turn with no script signal (a bare "1", a phone number),
    # keep the conversation's STICKY language so we never flip mid-flow; fall
    # back to the selected/stored preference only when there's no sticky value.
    # When NO language is known at all (fresh SwiftChat thread, no hint), leave
    # it unset so language_gate can ask.
    selected = body.get("language") if body.get("language") in ("mr", "hi", "en") else ustate.get("language")
    sticky = sess.get("reply_language")
    detected = _reply_language(user_text, selected)
    # Only resolve a reply language once the conversation HAS a language context
    # (an explicit hint, or a sticky value from a prior turn). A truly fresh
    # thread with no hint is left unset so language_gate can ask. Within a
    # context, the script the user WROTE in wins; an ambiguous turn (a bare
    # "1"/phone number) keeps the sticky language rather than resetting it.
    reply_language = None
    if selected or sticky:
        reply_language = detected or sticky or selected
        if reply_language:
            state["language"] = reply_language

    before = len(state["messages"])
    result = await yatra_graph.ainvoke(state)
    after_msgs = result.get("messages", [])

    # Persist transcript + intake (conversation-scoped); language/yatra (user-scoped).
    session_store.save(
        conv_id,
        messages=after_msgs,
        reg_stage=result.get("reg_stage"),
        reg_fields=result.get("reg_fields"),
        reply_language=reply_language or result.get("language"),
    )
    # Persist the SELECTED language (switcher/ask-flow result), not the
    # per-message detected reply language, so the user's preference is stable.
    await persistence.set_user_state(
        user_id,
        language=(selected or result.get("language")),
        active_yatra=result.get("active_yatra"),
    )

    # New assistant text this turn = anything appended past `before`.
    new_texts = [str(m.content) for m in after_msgs[before:] if isinstance(m, AIMessage)]
    reply = _clean("\n\n".join(t for t in new_texts if t.strip()))
    if not reply:
        reply = "🙏"  # never stream empty — SwiftChat 422s on empty text

    stream_id = f"stream.agent.{uuid.uuid4()}"
    yield {"event": "meta", "data": json.dumps({"stream_id": stream_id})}
    yield {"event": "message",
           "data": json.dumps({"message": {"content": [{"type": "text", "text": {"value": ""}}]}})}
    # Stream the reply as a single append (chunking is a later optimisation).
    yield {"event": "delta",
           "data": json.dumps({"p": "/message/content/0/text/value", "o": "append", "v": reply})}
    yield {"event": "end", "data": json.dumps({})}
    yield {"event": "done", "data": "[DONE]"}


@app.get("/api/lostfound")
async def api_lostfound_list(yatra: str | None = None, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    return await persistence.list_lost_found(yatra)


@app.post("/api/lostfound")
async def api_lostfound_create(request: Request, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    b = await request.json()
    kind = b.get("kind", "person")
    lid = await persistence.create_lost_found(
        kind=kind, name=b.get("name", ""), description=b.get("description", ""),
        last_seen=b.get("last_seen", ""), reporter_name=b.get("reporter_name", ""),
        reporter_phone=b.get("reporter_phone", ""), yatra=b.get("yatra"), yatra_id=b.get("yatra_id"))
    # A missing PERSON is an emergency — also raise an SOS so the control room /
    # war-room SOS feed picks it up immediately (lost & found built on SOS).
    if kind == "person":
        await persistence.create_sos(
            b.get("reporter_phone") or "lost-found", yatra=b.get("yatra"), yatra_id=b.get("yatra_id"),
            location=b.get("last_seen"), nature=f"Missing person: {b.get('name', '')}".strip())
    return {"id": lid}


@app.post("/api/lostfound/{lid}/status")
async def api_lostfound_status(lid: str, request: Request, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    b = await request.json()
    ok = await persistence.set_lost_found_status(lid, b.get("status", "reunited"))
    if not ok:
        raise HTTPException(status_code=404, detail="report not found")
    return {"ok": True}


@app.post("/api/voice/token")
async def api_voice_token(request: Request, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    if not settings.VOICE_ENABLED:
        raise HTTPException(status_code=503, detail="voice not configured")
    body = await request.json()
    user_id = body.get("user_id", "web-tester")
    yatra = body.get("yatra")
    language = body.get("language")
    room = f"yatra-voice-{user_id}-{uuid.uuid4().hex[:8]}"
    from livekit import api  # lazy — keeps module import + 503/sos paths creds-free
    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(user_id)
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )
    # Explicit dispatch so our agent_name worker joins THIS room. Best-effort:
    # if the worker/dispatch service isn't reachable, still return the token
    # (client can connect; worker joins when it comes up).
    try:
        lkapi = api.LiveKitAPI(settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=settings.AGENT_NAME,
                room=room,
                metadata=json.dumps({"user_id": user_id, "yatra": yatra, "language": language}),
            )
        )
        await lkapi.aclose()
    except Exception as e:
        print(f"[voice] dispatch failed (returning token anyway): {e}", flush=True)
    return {"url": settings.LIVEKIT_URL, "token": token, "room": room}


@app.post("/api/voice/sos")
async def api_voice_sos(request: Request, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    body = await request.json()
    sos_id = await persistence.create_sos(
        body.get("user_id", "voice-caller"),
        yatra=body.get("yatra"),
        yatra_id=body.get("yatra_id"),
        location=body.get("location"),
        nature=body.get("nature"),
    )
    return {"sos_id": sos_id}


@app.post("/messages")
async def messages(request: Request, x_api_key: str | None = Header(default=None)):
    if x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="bad api key")
    body = await request.json()
    return EventSourceResponse(_stream_turn(body))
