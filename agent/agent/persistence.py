"""user_state / registrations / sos_events access. Uses Postgres when
settings.DB_ENABLED (and a pool is available), else in-process dicts.
All functions are async and safe to call with the DB off. The DB branch is
exercised only when DATABASE_URL is set (prod / Plan 4); tests cover the
in-memory path."""
from __future__ import annotations
import json
from datetime import datetime, timezone

from agent.config import get_settings
from agent import db

_USER_STATE: dict[str, dict] = {}
_REGISTRATIONS: dict[str, dict] = {}   # yatra_id -> row
_SOS: list[dict] = []
_SEQ = {"n": 0}

_PREFIX = {"pandharpur": "PWARI", "kumbh": "KUMBH"}


def reset() -> None:
    """Test hook — clear in-memory stores + id counter."""
    _USER_STATE.clear()
    _REGISTRATIONS.clear()
    _SOS.clear()
    _SEQ["n"] = 0


def _next() -> int:
    _SEQ["n"] += 1
    return _SEQ["n"]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


async def _pool():
    if get_settings().DB_ENABLED:
        return await db.get_pool()
    return None


# ── user_state ──────────────────────────────────────────────────────
async def get_user_state(user_id: str) -> dict:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT state FROM user_state WHERE user_id=%s", (user_id,))
                row = await cur.fetchone()
                return dict(row["state"]) if row and row.get("state") else {}
    return dict(_USER_STATE.get(user_id, {}))


async def set_user_state(user_id: str, *, language: str | None = None, active_yatra: str | None = None,
                        reg_stage: str | None = None, reg_fields: dict | None = None) -> None:
    state = await get_user_state(user_id)
    if language is not None:
        state["language"] = language
    if active_yatra is not None:
        state["active_yatra"] = active_yatra
    if reg_stage is not None:
        state["reg_stage"] = reg_stage
    if reg_fields is not None:
        state["reg_fields"] = reg_fields
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO user_state(user_id,state,updated_at) VALUES(%s,%s,NOW()) "
                    "ON CONFLICT(user_id) DO UPDATE SET state=EXCLUDED.state, updated_at=NOW()",
                    (user_id, json.dumps(state)),
                )
            await conn.commit()
        return
    _USER_STATE[user_id] = state


# ── registrations ───────────────────────────────────────────────────
async def create_registration(user_id: str, *, yatra: str, name: str, phone: str,
                              group_name: str, emergency_contact: str, medical_flags: str) -> str:
    yatra_id = f"{_PREFIX.get(yatra, 'YATRA')}-{_today()}-{_next():04d}"
    row = {
        "yatra_id": yatra_id, "user_id": user_id, "yatra": yatra, "name": name,
        "phone": phone, "group_name": group_name, "emergency_contact": emergency_contact,
        "medical_flags": medical_flags,
    }
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO registrations(yatra_id,user_id,yatra,name,phone,group_name,emergency_contact,medical_flags) "
                    "VALUES(%(yatra_id)s,%(user_id)s,%(yatra)s,%(name)s,%(phone)s,%(group_name)s,%(emergency_contact)s,%(medical_flags)s)",
                    row,
                )
            await conn.commit()
    else:
        _REGISTRATIONS[yatra_id] = row
    return yatra_id


async def get_registration_for_user(user_id: str) -> dict | None:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM registrations WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
                    (user_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None
    hits = [r for r in _REGISTRATIONS.values() if r["user_id"] == user_id]
    return hits[-1] if hits else None


async def get_registration_by_id(yatra_id: str) -> dict | None:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM registrations WHERE yatra_id=%s",
                    (yatra_id,),
                )
                row = await cur.fetchone()
                return dict(row) if row else None
    return dict(_REGISTRATIONS[yatra_id]) if yatra_id in _REGISTRATIONS else None


# ── sos_events ──────────────────────────────────────────────────────
async def create_sos(user_id: str, *, yatra: str | None = None, yatra_id: str | None = None,
                     location: str | None = None, nature: str | None = None) -> str:
    sid = f"SOS-{_today()}-{_next():04d}"
    row = {"id": sid, "user_id": user_id, "yatra": yatra, "yatra_id": yatra_id,
           "location": location, "nature": nature, "status": "open"}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO sos_events(id,user_id,yatra,yatra_id,location,nature,status) "
                    "VALUES(%(id)s,%(user_id)s,%(yatra)s,%(yatra_id)s,%(location)s,%(nature)s,%(status)s)",
                    row,
                )
            await conn.commit()
    else:
        _SOS.append(row)
    return sid


async def list_sos() -> list[dict]:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM sos_events ORDER BY created_at DESC")
                return [dict(r) for r in await cur.fetchall()]
    return list(_SOS)
