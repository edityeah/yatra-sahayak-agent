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
import hashlib
import hmac
import io
import json
import logging
import re
import time
import uuid
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage

from agent.config import get_settings
from agent.state import new_state
from agent.graph import yatra_graph
from agent import db
from agent import persistence
from agent import seed

load_dotenv()
settings = get_settings()


# ── logging: redact phone-number-like sequences from all log records ──
class _PiiFilter(logging.Filter):
    _PHONE = re.compile(r"\b(\d{10}|\d{12})\b")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._PHONE.sub("[redacted]", record.msg)
        return True


logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger().addFilter(_PiiFilter())
log = logging.getLogger("yatra")


# ── security helpers ─────────────────────────────────────────────────
def _sig_valid(raw_body: bytes, signature: str | None) -> bool:
    """True if the request carries a valid SwiftChat HMAC signature. Always
    False when no secret is configured (so callers fail closed on that path)."""
    secret = settings.SWIFTCHAT_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature.split("=", 1)[-1].strip()  # tolerate "sha256=" prefix
    return hmac.compare_digest(expected, provided)


_RL: dict[str, list[float]] = {}


def _rate_limited(key: str) -> bool:
    limit = settings.RATE_LIMIT_PER_MIN
    if limit <= 0:
        return False
    now = time.time()
    bucket = _RL.setdefault(key, [])
    cutoff = now - 60.0
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False

app = FastAPI(title="Yatra Sahayak Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    # Log the full error server-side; never leak stack traces to the client.
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "internal error"})


@app.on_event("startup")
async def _startup() -> None:
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
            log.info("Sentry error tracking enabled")
        except Exception as e:  # pragma: no cover - optional dep
            log.warning("SENTRY_DSN set but sentry_sdk unavailable: %s", e)
    await db.run_migrations()
    # Production posture checks — loud warnings when a live (DB-backed) deploy
    # is running with insecure defaults, so they're caught in logs immediately.
    if settings.DB_ENABLED:
        if settings.ADMIN_API_KEY == settings.INTERNAL_API_KEY:
            log.warning("SECURITY: ADMIN_API_KEY == INTERNAL_API_KEY — officer/PII endpoints "
                        "are guarded by the browser-shipped key. Set a distinct ADMIN_API_KEY.")
        if settings.INTERNAL_API_KEY == "local-dev-key":
            log.warning("SECURITY: INTERNAL_API_KEY is the dev default. Set a real key.")
        if "*" in settings.CORS_ORIGINS:
            log.warning("SECURITY: CORS is open to '*'. Set CORS_ORIGINS to the webview origin(s).")


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


def _auth_level(x_api_key: str | None) -> str | None:
    """'admin' (officer/admin key) | 'internal' (browser key) | None."""
    if x_api_key == settings.ADMIN_API_KEY:
        return "admin"
    if x_api_key == settings.INTERNAL_API_KEY:
        return "internal"
    return None


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

    # Restore this conversation's transcript from durable session storage
    # (Postgres when enabled, in-memory otherwise). SwiftChat doesn't resend
    # prior turns and markers are stripped before streaming, so this is the
    # source of truth for history + in-progress intake across restarts/instances.
    sess = await persistence.get_session(conv_id)
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
    await persistence.save_session(
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
    level = _auth_level(x_api_key)
    if not level:
        raise HTTPException(status_code=401, detail="bad api key")
    rows = await persistence.list_lost_found(yatra)
    if level != "admin":
        # Public reunification board (yatri) — redact the reporter's PII;
        # officers (admin key) see full contact details.
        rows = [{k: v for k, v in r.items() if k not in ("reporter_phone", "reporter_name")} for r in rows]
    return rows


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


@app.post("/api/grievances")
async def api_grievance_create(request: Request, x_api_key: str | None = Header(default=None)):
    _require_key(x_api_key)
    b = await request.json()
    gid = await persistence.create_grievance(
        category=b.get("category", "other"), description=b.get("description", ""),
        location=b.get("location", ""), reporter_name=b.get("reporter_name", ""),
        reporter_phone=b.get("reporter_phone", ""), yatra=b.get("yatra"), yatra_id=b.get("yatra_id"))
    return {"id": gid}


@app.get("/api/grievances")
async def api_grievance_list(yatra: str | None = None, x_api_key: str | None = Header(default=None)):
    level = _auth_level(x_api_key)
    if not level:
        raise HTTPException(status_code=401, detail="bad api key")
    rows = await persistence.list_grievances(yatra)
    if level != "admin":
        rows = [{k: v for k, v in r.items() if k not in ("reporter_phone", "reporter_name")} for r in rows]
    return rows


@app.post("/api/grievances/{gid}/status")
async def api_grievance_status(gid: str, request: Request, x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)
    b = await request.json()
    ok = await persistence.set_grievance_status(gid, b.get("status", "resolved"))
    if not ok:
        raise HTTPException(status_code=404, detail="grievance not found")
    return {"ok": True}


@app.get("/api/alerts")
async def api_alerts_list(yatra: str | None = None, x_api_key: str | None = Header(default=None)):
    # Public read (pilgrims see active alerts); either key works.
    if not _auth_level(x_api_key):
        raise HTTPException(status_code=401, detail="bad api key")
    return await persistence.list_alerts(yatra, active_only=True)


@app.post("/api/alerts")
async def api_alert_create(request: Request, x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)   # officers only
    b = await request.json()
    aid = await persistence.create_alert(
        title=b.get("title", ""), message=b.get("message", ""),
        severity=b.get("severity", "info"), yatra=b.get("yatra"))
    return {"id": aid}


@app.post("/api/alerts/{aid}/deactivate")
async def api_alert_deactivate(aid: str, x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)
    ok = await persistence.set_alert_active(aid, False)
    if not ok:
        raise HTTPException(status_code=404, detail="alert not found")
    return {"ok": True}


def _require_officer(x_admin_key: str | None, user_id: str | None, sig_ok: bool) -> None:
    """Officer war-room gate: the ADMIN_API_KEY (dashboard) OR an allowlisted
    SwiftChat user_id WITH a verified webhook signature (the officer bot). The
    allowlist alone is not enough — a raw user_id is spoofable, so it must be
    signed. If no webhook secret is configured, only the admin key works."""
    if x_admin_key == settings.ADMIN_API_KEY:
        return
    if sig_ok and user_id and user_id in settings.OFFICER_IDS:
        return
    raise HTTPException(status_code=403, detail="officer access required")


@app.get("/api/sos")
async def api_sos_list(status: str | None = None, x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)
    rows = await persistence.list_sos()
    if status:
        rows = [r for r in rows if (r.get("status") or "open") == status]
    return rows


@app.post("/api/sos/{sos_id}/status")
async def api_sos_status(sos_id: str, request: Request, x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)
    b = await request.json()
    ok = await persistence.set_sos_status(sos_id, b.get("status", "resolved"))
    if not ok:
        raise HTTPException(status_code=404, detail="sos not found")
    return {"ok": True}


@app.get("/api/officer/summary")
async def api_officer_summary(x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)
    return await persistence.officer_summary()


async def _officer_stream(body: dict) -> AsyncIterator[dict]:
    from agent.officer import officer_reply
    reply = _clean(await officer_reply(_extract_user_text(body.get("message", {})))) or "🙏"
    stream_id = f"stream.officer.{uuid.uuid4()}"
    yield {"event": "meta", "data": json.dumps({"stream_id": stream_id})}
    yield {"event": "message",
           "data": json.dumps({"message": {"content": [{"type": "text", "text": {"value": ""}}]}})}
    yield {"event": "delta",
           "data": json.dumps({"p": "/message/content/0/text/value", "o": "append", "v": reply})}
    yield {"event": "end", "data": json.dumps({})}
    yield {"event": "done", "data": "[DONE]"}


@app.post("/officer/messages")
async def officer_messages(request: Request,
                           x_api_key: str | None = Header(default=None),
                           x_admin_key: str | None = Header(default=None)):
    raw = await request.body()
    sig_ok = _sig_valid(raw, request.headers.get(settings.WEBHOOK_SIG_HEADER))
    body = json.loads(raw or b"{}")
    # Admin key (dashboard) via X-Admin-Key/X-API-Key, or a SIGNED officer-bot
    # request whose user_id is allowlisted.
    _require_officer(x_admin_key or x_api_key, body.get("user_id"), sig_ok)
    if _rate_limited(f"officer:{body.get('user_id') or (request.client.host if request.client else '?')}"):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    return EventSourceResponse(_officer_stream(body))


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
        log.warning("voice dispatch failed (returning token anyway): %s", e)
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
    key = body.get("user_id") or (request.client.host if request.client else "?")
    if _rate_limited(f"msg:{key}"):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    return EventSourceResponse(_stream_turn(body))
