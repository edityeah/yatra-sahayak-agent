"""FastAPI webhook — entrypoint the SwiftChat platform (or curl) hits.

SSE contract (added in Task 8) mirrors swift-learning-agent/agent/webhook.py:
  event: meta    data: {"stream_id": "..."}
  event: message data: {"message": {"content": [{"type":"text","text":{"value":""}}]}}
  event: delta   data: {"p":"/message/content/0/text/value","o":"append","v":"..."}
  event: end     data: {}
  event: done    data: [DONE]
"""
from __future__ import annotations
import json
import re
import uuid
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage

from agent.config import get_settings
from agent.state import new_state
from agent.graph import yatra_graph
from agent import db
from agent import session_store
from agent import persistence

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


_MARKER_RE = re.compile(r"\[(?:lang:(?:mr|hi|en)|yatra:(?:pandharpur|kumbh)|yatra-ask)\]")


def _clean(text: str) -> str:
    """Strip internal state markers before showing text to the user."""
    return _MARKER_RE.sub("", text or "").strip()


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

    # Language + yatra persist per-user via the persistence layer (DB when
    # enabled, memory otherwise); the transcript stays in the session store.
    ustate = await persistence.get_user_state(user_id)
    if ustate.get("language"):
        state["language"] = ustate["language"]
    if ustate.get("active_yatra"):
        state["active_yatra"] = ustate["active_yatra"]
    if ustate.get("reg_stage"):
        state["reg_stage"] = ustate["reg_stage"]
    if ustate.get("reg_fields"):
        state["reg_fields"] = ustate["reg_fields"]

    before = len(state["messages"])
    result = await yatra_graph.ainvoke(state)
    after_msgs = result.get("messages", [])

    # Persist the updated transcript + any newly-resolved language / yatra.
    session_store.save(conv_id, messages=after_msgs)
    await persistence.set_user_state(
        user_id,
        language=result.get("language"),
        active_yatra=result.get("active_yatra"),
        reg_stage=result.get("reg_stage"),
        reg_fields=result.get("reg_fields"),
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


@app.post("/messages")
async def messages(request: Request, x_api_key: str | None = Header(default=None)):
    if x_api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="bad api key")
    body = await request.json()
    return EventSourceResponse(_stream_turn(body))
