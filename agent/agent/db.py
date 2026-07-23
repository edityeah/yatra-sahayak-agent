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
  group_name     TEXT,
  emergency_contact TEXT,
  medical_flags  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
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
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await _pool.open()
    return _pool
