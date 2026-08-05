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
-- Conversation-scoped state (transcript + in-progress registration intake +
-- sticky reply language). Durable so it survives restarts and is shared
-- across instances — the in-memory session_store was single-process only.
CREATE TABLE IF NOT EXISTS sessions (
  conversation_id TEXT PRIMARY KEY,
  data            JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
CREATE TABLE IF NOT EXISTS lost_found (
  id             TEXT PRIMARY KEY,
  kind           TEXT NOT NULL,            -- 'person' | 'item'
  status         TEXT NOT NULL DEFAULT 'open',   -- 'open' | 'reunited'
  name           TEXT,
  description    TEXT,
  last_seen      TEXT,
  reporter_name  TEXT,
  reporter_phone TEXT,
  yatra          TEXT,
  yatra_id       TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS grievances (
  id             TEXT PRIMARY KEY,
  category       TEXT,
  description    TEXT,
  location       TEXT,
  reporter_name  TEXT,
  reporter_phone TEXT,
  yatra          TEXT,
  yatra_id       TEXT,
  status         TEXT NOT NULL DEFAULT 'open',   -- 'open' | 'in_progress' | 'resolved'
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS alerts (
  id             TEXT PRIMARY KEY,
  title          TEXT,
  message        TEXT,
  severity       TEXT NOT NULL DEFAULT 'info',    -- 'info' | 'warning' | 'danger'
  yatra          TEXT,
  active         BOOLEAN NOT NULL DEFAULT TRUE,
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
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS routed_to TEXT;
-- Contact snapshot for callers with no registration (voice SOS, walk-ins).
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS reporter_name TEXT;
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS reporter_phone TEXT;
-- Exact incident coordinates (captured when the pilgrim shares their live
-- location on SOS). Drives nearest-police-control routing; NULL falls back to
-- the district control room.
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION;
ALTER TABLE sos_events ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION;
-- Incident timeline: every action an officer takes on an SOS is logged here
-- (acknowledgement, unit dispatch, resolution, plain notes) with who did it and
-- structured detail (unit name, contact, ETA, outcome). This is the audit trail
-- the control room / 112 CAD would keep.
CREATE TABLE IF NOT EXISTS sos_updates (
  id             BIGSERIAL PRIMARY KEY,
  sos_id         TEXT NOT NULL,
  status         TEXT,                              -- status set by this update (null = comment only)
  actor          TEXT,                              -- officer who logged it
  note           TEXT,
  meta           JSONB NOT NULL DEFAULT '{}'::jsonb, -- unit / contact / eta / outcome
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS sos_updates_sos_idx ON sos_updates(sos_id, created_at);
-- Pass-scan events at gates/halts/ghats. Aggregated into a live occupancy
-- heatmap for the control room — a headcount per checkpoint per time window,
-- with NO tracking of anyone between checkpoints (privacy-preserving crowd sense).
CREATE TABLE IF NOT EXISTS checkpoint_scans (
  id             BIGSERIAL PRIMARY KEY,
  checkpoint_id  TEXT NOT NULL,
  yatra          TEXT,
  yatra_id       TEXT,
  user_id        TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS checkpoint_scans_idx ON checkpoint_scans(checkpoint_id, created_at);
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
    # Commit PER STATEMENT (autocommit) so one failing migration can't roll back
    # the others. Previously the whole batch ran in a single transaction, so a
    # single failure reverted every ADD COLUMN — which is exactly how the live DB
    # ended up with routed_to/sos_updates but NOT lat/lng. Each statement is
    # idempotent (IF NOT EXISTS), so re-running is safe; failures are logged
    # individually instead of silently reverting good migrations.
    try:
        async with await psycopg.AsyncConnection.connect(url, autocommit=True) as conn:
            async with conn.cursor() as cur:
                ok = failed = 0
                for stmt in [s.strip() for s in MIGRATIONS_SQL.split(";") if s.strip()]:
                    try:
                        await cur.execute(stmt)
                        ok += 1
                    except Exception as e:   # noqa: BLE001 — keep going, log the culprit
                        failed += 1
                        print(f"[run_migrations] STMT FAILED: {stmt[:70]!r}: {e!r}", flush=True)
        print(f"[run_migrations] complete ({ok} ok, {failed} failed)", flush=True)
    except Exception as e:
        print(f"[run_migrations] CONNECTION FAILED: {e!r}", flush=True)


async def schema_probe() -> dict:
    """Lightweight check of whether the SOS-related migrations actually applied
    on this deploy's DB — so /version can tell a stale deploy from a failed
    migration without needing DB console access. Never raises."""
    settings = get_settings()
    if not settings.DATABASE_URL:
        return {"db": False}
    out: dict = {"db": True}
    try:
        url = _sanitize_pg_url(settings.DIRECT_URL or settings.DATABASE_URL)
        async with await psycopg.AsyncConnection.connect(url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='sos_events'")
                cols = {r[0] for r in await cur.fetchall()}
                await cur.execute("SELECT to_regclass('public.sos_updates')")
                updates_tbl = (await cur.fetchone())[0] is not None
        out.update({
            "sos_events.lat": "lat" in cols,
            "sos_events.routed_to": "routed_to" in cols,
            "sos_updates": updates_tbl,
        })
    except Exception as e:   # noqa: BLE001
        out["probe_error"] = repr(e)
    return out


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
