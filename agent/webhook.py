"""FastAPI webhook — entrypoint the SwiftChat platform (or curl) hits.

SSE contract (added in Task 8) mirrors swift-learning-agent/agent/webhook.py:
  event: meta    data: {"stream_id": "..."}
  event: message data: {"message": {"content": [{"type":"text","text":{"value":""}}]}}
  event: delta   data: {"p":"/message/content/0/text/value","o":"append","v":"..."}
  event: end     data: {}
  event: done    data: [DONE]
"""
from __future__ import annotations
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.config import get_settings

load_dotenv()
settings = get_settings()

app = FastAPI(title="Yatra Sahayak Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "yatra-sahayak-agent", "db": settings.DB_ENABLED}
