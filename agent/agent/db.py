"""Async Postgres access. DB is OPTIONAL — when DATABASE_URL is unset,
get_pool() returns None and callers fall back to in-memory behaviour.
Ported from swift-learning-agent/agent/agent/db.py."""
from __future__ import annotations
import logging

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from agent.config import get_settings

log = logging.getLogger(__name__)
_pool: AsyncConnectionPool | None = None

# Minimal spine schema. user_state persists language + yatra choice per user
# so we don't depend on client-sent history. Activity tables land in later plans.
MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS yatris (
  user_id     TEXT PRIMARY KEY,
  name        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS user_state (
  user_id     TEXT PRIMARY KEY,
  state       JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS registrations (
  yatra_id       TEXT PRIMARY KEY,
  user_id        TEXT NOT NULL,
  yatra          TEXT NOT NULL,
  name           TEXT,
  phone          TEXT,
  age            TEXT,
  id_type        TEXT,
  group_name     TEXT,
  group_size     INTEGER DEFAULT 1,
  group_id       TEXT,
  is_primary     BOOLEAN DEFAULT TRUE,
  emergency_contact TEXT,
  medical_flags  TEXT,
  mobile_verified BOOLEAN DEFAULT FALSE,
  ekyc_verified  BOOLEAN DEFAULT FALSE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS age TEXT;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS id_type TEXT;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS group_size INTEGER DEFAULT 1;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS group_id TEXT;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT TRUE;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS mobile_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS ekyc_verified BOOLEAN DEFAULT FALSE;
CREATE TABLE IF NOT EXISTS sos_events (
  id             TEXT PRIMARY KEY,
  user_id        TEXT NOT NULL,
  yatra          TEXT,
  yatra_id       TEXT,
  location       TEXT,
  nature         TEXT,
  status         TEXT NOT NULL DEFAULT 'open',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _sanitize_pg_url(url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote
    parts = urlsplit(url)
    if parts.password:
        safe_pw = quote(parts.password, safe="")
        user = quote(parts.username or "", safe="")
        host = parts.hostname or ""
        netloc = f"{user}:{safe_pw}@{host}"
        if parts.port:
            netloc += f":{parts.port}"
        parts = parts._replace(netloc=netloc)
    allowed = {"sslmode", "connect_timeout", "application_name", "options"}
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k in allowed]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


async def run_migrations() -> None:
    settings = get_settings()
    raw = settings.DIRECT_URL or settings.DATABASE_URL
    if not raw:
        log.info("run_migrations: no DATABASE_URL — skipping (DB disabled)")
        return
    url = _sanitize_pg_url(raw)
    try:
        async with await psycopg.AsyncConnection.connect(url) as conn:
            async with conn.cursor() as cur:
                for stmt in [s.strip() for s in MIGRATIONS_SQL.split(";") if s.strip()]:
                    await cur.execute(stmt)
            await conn.commit()
        print("[run_migrations] complete", flush=True)
    except Exception as e:
        print(f"[run_migrations] FAILED: {e!r}", flush=True)


async def get_pool() -> AsyncConnectionPool | None:
    global _pool
    if _pool is not None:
        return _pool
    settings = get_settings()
    if not settings.DATABASE_URL:
        return None
    _pool = AsyncConnectionPool(
        _sanitize_pg_url(settings.DATABASE_URL),
        min_size=1, max_size=5, timeout=5.0,
        # prepare_threshold=None disables psycopg's automatic prepared
        # statements. REQUIRED for Supabase's transaction-mode pooler (port
        # 6543 / pgbouncer): pooled connections are multiplexed, so a prepared
        # statement created on one backend isn't visible on the next, causing
        # intermittent "prepared statement does not exist" errors. Harmless on
        # a direct/session connection.
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
        open=False,
    )
    await _pool.open()
    return _pool
