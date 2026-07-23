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

    # Webhook auth — every caller (SwiftChat, curl) must send X-API-Key.
    INTERNAL_API_KEY: str = os.environ.get("INTERNAL_API_KEY", "local-dev-key")

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
