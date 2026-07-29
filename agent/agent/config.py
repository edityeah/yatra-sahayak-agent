"""Config — thin env-var loader with sensible local defaults."""
from __future__ import annotations
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    LLM_MAIN_MODEL: str = os.environ.get("LLM_MAIN_MODEL", "gpt-4o-mini")

    # CORS — comma-separated allowed origins. "*" is fine for dev but should be
    # locked to the webview origin(s) in production.
    CORS_ORIGINS: list = [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()
    ] or ["*"]

    # Webhook auth — every caller (SwiftChat, curl) must send X-API-Key.
    # NOTE: this key is shipped to the browser by the webview (VITE_AGENT_KEY),
    # so it must NOT guard officer/admin data (pilgrim PII). Use ADMIN_API_KEY.
    INTERNAL_API_KEY: str = os.environ.get("INTERNAL_API_KEY", "local-dev-key")

    # Officer/admin auth — guards endpoints that expose pilgrim PII (the
    # registrations export). MUST be a separate secret from INTERNAL_API_KEY
    # (that one is public via the webview). Defaults to the internal key ONLY
    # for local dev/tests; set a distinct value in production.
    ADMIN_API_KEY: str = os.environ.get(
        "ADMIN_API_KEY", os.environ.get("INTERNAL_API_KEY", "local-dev-key")
    )

    # Officer war-room allowlist — comma-separated SwiftChat user_ids permitted
    # to use the officer bot (/officer/messages). The dashboard + officer chat
    # also accept the ADMIN_API_KEY as an alternative (webview gate).
    OFFICER_IDS: set = frozenset(
        i.strip() for i in os.environ.get("OFFICER_IDS", "").split(",") if i.strip()
    )

    # SwiftChat webhook HMAC verification. When set, the officer-bot allowlist
    # path requires a valid signature (else the ADMIN_API_KEY is the only way
    # in) — so a spoofed user_id can't reach officer data.
    SWIFTCHAT_WEBHOOK_SECRET: str = os.environ.get("SWIFTCHAT_WEBHOOK_SECRET", "").strip()
    WEBHOOK_SIG_HEADER: str = os.environ.get("WEBHOOK_SIG_HEADER", "X-Signature").strip()

    # Rate limiting (per user_id/IP, per minute) on the chat endpoints. 0 = off.
    # In-process only — a multi-instance deploy needs a shared store (Redis).
    RATE_LIMIT_PER_MIN: int = int(os.environ.get("RATE_LIMIT_PER_MIN", "30") or "30")

    # Observability.
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    SENTRY_DSN: str = os.environ.get("SENTRY_DSN", "").strip()

    # Public base URL of the deployed webview. Every markdown link the agent
    # returns must be absolute — SwiftChat calls new URL(link) on it.
    PUBLIC_WEBVIEW_BASE: str = os.environ.get(
        "PUBLIC_WEBVIEW_BASE", "http://localhost:5174"
    ).rstrip("/")

    # SwiftChat outbound — where we POST rich blocks / the final reply.
    # Empty ⇒ SSE-only mode (local dev + curl).
    SWIFTCHAT_AGENT_ID:     str = os.environ.get("SWIFTCHAT_AGENT_ID", "").strip()
    SWIFTCHAT_API_KEY:      str = os.environ.get("SWIFTCHAT_API_KEY", "").strip()
    SWIFTCHAT_MESSAGES_URL: str = os.environ.get("SWIFTCHAT_MESSAGES_URL", "").strip()

    # Database — Supabase Postgres. Empty ⇒ in-memory (no cross-restart state).
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "").strip()
    DIRECT_URL:   str = os.environ.get("DIRECT_URL", os.environ.get("DATABASE_URL", "")).strip()
    DB_ENABLED:   bool = bool(os.environ.get("DATABASE_URL", "").strip())

    # IMD weather API. Empty ⇒ always use the cached fallback (data/weather_fallback.json).
    # When set, may contain a "{yatra}" placeholder, e.g. https://host/forecast?loc={yatra}
    IMD_API_URL: str = os.environ.get("IMD_API_URL", "").strip()

    # Root of shared seed data (rates, routes, drills). data/ is at repo root,
    # two levels up from this file (agent/agent/config.py).
    DATA_DIR: str = os.environ.get(
        "DATA_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data")),
    )

    # LiveKit voice (Plan 5). Empty ⇒ voice disabled (503 from /api/voice/token).
    LIVEKIT_URL:        str = os.environ.get("LIVEKIT_URL", "").strip()
    LIVEKIT_API_KEY:    str = os.environ.get("LIVEKIT_API_KEY", "").strip()
    LIVEKIT_API_SECRET: str = os.environ.get("LIVEKIT_API_SECRET", "").strip()
    AGENT_NAME:         str = os.environ.get("AGENT_NAME", "yatra-sahayak-voice")
    VOICE_ENABLED:      bool = bool(os.environ.get("LIVEKIT_URL", "").strip()
                                    and os.environ.get("LIVEKIT_API_KEY", "").strip()
                                    and os.environ.get("LIVEKIT_API_SECRET", "").strip())

    # Voice worker → web service callback (raise_sos tool). The worker has no
    # DB access of its own; it POSTs to the web service's /api/voice/sos.
    AGENT_API_HOST: str = os.environ.get("AGENT_API_HOST", "http://localhost:8000").rstrip("/")
    AGENT_API_KEY:  str = os.environ.get("AGENT_API_KEY", os.environ.get("INTERNAL_API_KEY", "local-dev-key"))

    # Single-origin deploy: when set to a built webview/dist, the agent also
    # SERVES the web UI (so one host — e.g. a Cloudflare tunnel at
    # yatri.adityeah.ai — serves both the app and the API). Empty ⇒ API only
    # (the Vercel + Render split keeps working unchanged).
    WEBVIEW_DIST: str = os.environ.get("WEBVIEW_DIST", "").strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
