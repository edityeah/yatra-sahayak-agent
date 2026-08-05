"""user_state / registrations / sos_events access. Uses Postgres when
settings.DB_ENABLED (and a pool is available), else in-process dicts.
All functions are async and safe to call with the DB off. The DB branch is
exercised only when DATABASE_URL is set (prod / Plan 4); tests cover the
in-memory path."""
from __future__ import annotations
import json
import random
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage

from agent.config import get_settings
from agent import db

_USER_STATE: dict[str, dict] = {}
_REGISTRATIONS: dict[str, dict] = {}   # yatra_id -> row
_SOS: list[dict] = []
_SOS_UPDATES: list[dict] = []          # incident timeline (audit trail per SOS)
_SCANS: list[dict] = []                # pass-scan events at checkpoints (crowd sense)
_LOSTFOUND: list[dict] = []            # lost & found reports
_GRIEVANCES: list[dict] = []           # pilgrim grievances/complaints
_ALERTS: list[dict] = []               # officer → pilgrim broadcast alerts
_SESSIONS: dict[str, dict] = {}        # conversation_id -> stored (serialized) state
# Per-process id counter. Seeded at a RANDOM base (not 0) so a process
# restart — deploy, cold start, an OOM — doesn't reset to 0001 and collide with
# an id already in the DB (yatra_id etc. are primary keys). create_registration
# also retries on a duplicate-key as a hard guarantee.
_SEQ = {"n": random.randint(1000, 8999)}

_PREFIX = {"pandharpur": "PWARI", "kumbh": "KUMBH"}


def reset() -> None:
    """Test hook — clear in-memory stores + id counter."""
    _USER_STATE.clear()
    _REGISTRATIONS.clear()
    _SOS.clear()
    _SOS_UPDATES.clear()
    _SCANS.clear()
    _LOSTFOUND.clear()
    _GRIEVANCES.clear()
    _ALERTS.clear()
    _SESSIONS.clear()
    _SEQ["n"] = 0


def _next() -> int:
    _SEQ["n"] += 1
    return _SEQ["n"]


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


# ── sessions (conversation-scoped: transcript + intake + sticky lang) ─
def _ser_msgs(msgs) -> list[dict]:
    return [{"r": "ai" if isinstance(m, AIMessage) else "human", "c": str(m.content)} for m in (msgs or [])]


def _deser_msgs(rows) -> list:
    return [AIMessage(content=r["c"]) if r.get("r") == "ai" else HumanMessage(content=r["c"]) for r in (rows or [])]


async def _load_session_raw(conversation_id: str) -> dict:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT data FROM sessions WHERE conversation_id=%s", (conversation_id,))
                row = await cur.fetchone()
                return dict(row["data"]) if row and row.get("data") else {}
    return dict(_SESSIONS.get(conversation_id, {}))


async def get_session(conversation_id: str) -> dict:
    """Conversation state with `messages` rehydrated into LangChain objects."""
    data = await _load_session_raw(conversation_id)
    if data.get("messages") is not None:
        data["messages"] = _deser_msgs(data["messages"])
    return data


_UNSET = object()  # sentinel: distinguishes "don't touch" from "set to None"


async def save_session(conversation_id: str, *, messages: list | None = None, reg_stage: str | None = None,
                       reg_fields: dict | None = None, reply_language: str | None = None,
                       awaiting: str | None | object = _UNSET) -> None:
    """Partial upsert — only the provided fields are updated (read-modify-write)."""
    data = await _load_session_raw(conversation_id)
    if messages is not None:
        data["messages"] = _ser_msgs(messages)
    if reg_stage is not None:
        data["reg_stage"] = reg_stage
    if reg_fields is not None:
        data["reg_fields"] = reg_fields
    if reply_language is not None:
        data["reply_language"] = reply_language
    # `awaiting` uses a sentinel so passing None explicitly CLEARS it (the
    # weather origin-ask is satisfied), while omitting it leaves it untouched.
    if awaiting is not _UNSET:
        data["awaiting"] = awaiting
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO sessions(conversation_id,data,updated_at) VALUES(%s,%s,NOW()) "
                    "ON CONFLICT(conversation_id) DO UPDATE SET data=EXCLUDED.data, updated_at=NOW()",
                    (conversation_id, json.dumps(data)),
                )
            await conn.commit()
        return
    _SESSIONS[conversation_id] = data


async def clear_session(conversation_id: str) -> None:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM sessions WHERE conversation_id=%s", (conversation_id,))
            await conn.commit()
        return
    _SESSIONS.pop(conversation_id, None)


# ── registrations ───────────────────────────────────────────────────
async def create_registration(user_id: str, *, yatra: str, name: str, phone: str,
                              group_name: str, emergency_contact: str, medical_flags: str,
                              age: str = "", id_type: str = "", group_size: int = 1,
                              group_id: str = "", is_primary: bool = True,
                              mobile_verified: bool = False, ekyc_verified: bool = False) -> str:
    base = dict(
        user_id=user_id, yatra=yatra, name=name, phone=phone, age=age, id_type=id_type,
        group_name=group_name, group_size=group_size, group_id=group_id, is_primary=is_primary,
        emergency_contact=emergency_contact, medical_flags=medical_flags,
        mobile_verified=mobile_verified, ekyc_verified=ekyc_verified,
    )
    pool = await _pool()
    if not pool:
        yatra_id = f"{_PREFIX.get(yatra, 'YATRA')}-{_today()}-{_next():04d}"
        _REGISTRATIONS[yatra_id] = {"yatra_id": yatra_id, **base}
        return yatra_id

    # Retry on a duplicate primary key (23505): a fresh process starts its
    # counter at a random base, but two starts could still collide with an
    # existing yatra_id — bump to the next id and retry rather than 500.
    last_err = None
    for _ in range(10):
        yatra_id = f"{_PREFIX.get(yatra, 'YATRA')}-{_today()}-{_next():04d}"
        row = {"yatra_id": yatra_id, **base}
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO registrations(yatra_id,user_id,yatra,name,phone,age,id_type,"
                        "group_name,group_size,group_id,is_primary,emergency_contact,medical_flags,"
                        "mobile_verified,ekyc_verified) "
                        "VALUES(%(yatra_id)s,%(user_id)s,%(yatra)s,%(name)s,%(phone)s,%(age)s,%(id_type)s,"
                        "%(group_name)s,%(group_size)s,%(group_id)s,%(is_primary)s,%(emergency_contact)s,"
                        "%(medical_flags)s,%(mobile_verified)s,%(ekyc_verified)s)",
                        row,
                    )
                await conn.commit()
            return yatra_id
        except Exception as e:
            last_err = e
            if getattr(e, "sqlstate", None) == "23505":
                continue   # duplicate id — try the next one
            raise          # any other DB error is real — surface it
    raise last_err


def new_group_id() -> str:
    """A short shared id linking one family's passes (a household batch)."""
    return f"GRP-{_today()}-{_next():04d}"


async def list_registrations_for_user(user_id: str) -> list[dict]:
    """Every pass registered from this device/account — for the yatri wallet.
    Newest first (primary passes sort ahead of members within a batch)."""
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM registrations WHERE user_id=%s "
                    "ORDER BY created_at DESC, is_primary DESC",
                    (user_id,),
                )
                return [dict(r) for r in await cur.fetchall()]
    hits = [r for r in _REGISTRATIONS.values() if r["user_id"] == user_id]
    return list(reversed(hits))


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


async def list_registrations() -> list[dict]:
    """All registrations, newest first — for the officer/admin export."""
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM registrations ORDER BY created_at DESC")
                return [dict(r) for r in await cur.fetchall()]
    return list(_REGISTRATIONS.values())


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
# Which official control the SOS is escalated to (simulated intervention). In
# production this is the ERSS-112 CAD / State Emergency Operations Centre.
_SOS_CONTROL = {
    "pandharpur": "Pune District Control Room · 112 / 1077",
    "kumbh": "Nashik District Control Room · 112 / 1077",
}
_SOS_CONTROL_DEFAULT = "State Emergency Control Centre · 112"


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    import math
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_control(yatra: str | None, lat: float, lng: float) -> dict | None:
    """The closest police station / control room to an incident, from the
    seeded per-route directory. Returns the entry plus its distance_km, or None
    when the yatra has no directory. This is what makes 'nearest police control'
    real once we have the pilgrim's coordinates."""
    from agent.seed import load
    try:
        controls = load("police_controls").get(yatra or "", [])
    except Exception:
        return None
    pts = [c for c in controls if isinstance(c.get("lat"), (int, float)) and isinstance(c.get("lng"), (int, float))]
    if not pts:
        return None
    best = min(pts, key=lambda c: _haversine_km(lat, lng, c["lat"], c["lng"]))
    return {**best, "distance_km": round(_haversine_km(lat, lng, best["lat"], best["lng"]), 1)}


def sos_control_for(yatra: str | None, lat: float | None = None, lng: float | None = None) -> str:
    """The escalation target label stored on an SOS. With coordinates, this is
    the NEAREST police control from the route directory (name · phone / 112,
    with distance). Without coordinates, it falls back to the district control
    room — which is why capturing the pilgrim's location on SOS matters."""
    if lat is not None and lng is not None:
        c = nearest_control(yatra, lat, lng)
        if c:
            name = c["name"]["en"] if isinstance(c.get("name"), dict) else c.get("name")
            phone = c.get("phone")
            tail = f" · {phone} / 112" if phone and phone != "112" else " · 112"
            dist = f" ({c['distance_km']} km away)" if c.get("distance_km") is not None else ""
            return f"{name}{tail}{dist}"
    return _SOS_CONTROL.get(yatra or "", _SOS_CONTROL_DEFAULT)


async def create_sos(user_id: str, *, yatra: str | None = None, yatra_id: str | None = None,
                     location: str | None = None, nature: str | None = None,
                     routed_to: str | None = None, reporter_name: str | None = None,
                     reporter_phone: str | None = None,
                     lat: float | None = None, lng: float | None = None) -> str:
    sid = f"SOS-{_today()}-{_next():04d}"
    # With coordinates, route to the NEAREST police control; else the district room.
    routed_to = routed_to or sos_control_for(yatra, lat, lng)
    # status starts "open" = escalated/awaiting-acknowledgement at the control room.
    row = {"id": sid, "user_id": user_id, "yatra": yatra, "yatra_id": yatra_id,
           "location": location, "nature": nature, "status": "open", "routed_to": routed_to,
           "reporter_name": reporter_name, "reporter_phone": reporter_phone,
           "lat": lat, "lng": lng}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO sos_events(id,user_id,yatra,yatra_id,location,nature,status,routed_to,"
                    "reporter_name,reporter_phone,lat,lng) "
                    "VALUES(%(id)s,%(user_id)s,%(yatra)s,%(yatra_id)s,%(location)s,%(nature)s,%(status)s,"
                    "%(routed_to)s,%(reporter_name)s,%(reporter_phone)s,%(lat)s,%(lng)s)",
                    row,
                )
            await conn.commit()
    else:
        _SOS.append({**row, "created_at": _now_iso()})
    # Seed the timeline: the escalation to the control room is the first event.
    await add_sos_update(sid, status="open", actor="system",
                         note=f"SOS raised · auto-escalated to {routed_to}", _touch_status=False)
    return sid


async def update_latest_open_sos_location(user_id: str, lat: float, lng: float) -> dict | None:
    """A pilgrim shared their live location right after raising an SOS. Attach it
    to their most recent still-open incident and RE-ROUTE to the nearest police
    control. Returns the updated SOS (with the new routed_to), or None."""
    rows = [r for r in await list_sos()
            if r.get("user_id") == user_id and (r.get("status") or "open") != "resolved"]
    if not rows:
        return None
    sos = rows[0]                       # list_sos is newest-first
    sid = sos["id"]
    routed_to = sos_control_for(sos.get("yatra"), lat, lng)
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE sos_events SET lat=%s, lng=%s, routed_to=%s WHERE id=%s",
                                  (lat, lng, routed_to, sid))
            await conn.commit()
    else:
        for r in _SOS:
            if r["id"] == sid:
                r.update(lat=lat, lng=lng, routed_to=routed_to)
    await add_sos_update(sid, actor="system",
                         note=f"Live location received · re-routed to {routed_to}", _touch_status=False)
    return await get_sos(sid)


async def list_sos() -> list[dict]:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM sos_events ORDER BY created_at DESC")
                return [dict(r) for r in await cur.fetchall()]
    return list(reversed(_SOS))


async def get_sos(sos_id: str) -> dict | None:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM sos_events WHERE id=%s", (sos_id,))
                row = await cur.fetchone()
                return dict(row) if row else None
    return next((dict(r) for r in _SOS if r["id"] == sos_id), None)


async def list_sos_updates(sos_id: str) -> list[dict]:
    """The incident timeline for one SOS, oldest → newest."""
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM sos_updates WHERE sos_id=%s ORDER BY created_at ASC, id ASC",
                    (sos_id,),
                )
                return [dict(r) for r in await cur.fetchall()]
    return [dict(u) for u in _SOS_UPDATES if u["sos_id"] == sos_id]


async def add_sos_update(sos_id: str, *, status: str | None = None, actor: str | None = None,
                         note: str | None = None, meta: dict | None = None,
                         _touch_status: bool = True) -> dict | None:
    """Log one action on an SOS to the timeline, and (optionally) advance its
    status. Returns the created update, or None if the SOS doesn't exist."""
    if await get_sos(sos_id) is None:
        return None
    import json as _json
    meta = meta or {}
    update = {"sos_id": sos_id, "status": status, "actor": actor or "officer",
              "note": note, "meta": meta}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO sos_updates(sos_id,status,actor,note,meta) "
                    "VALUES(%s,%s,%s,%s,%s::jsonb) RETURNING id, created_at",
                    (sos_id, status, update["actor"], note, _json.dumps(meta)),
                )
                r = await cur.fetchone()
                update["id"], update["created_at"] = r["id"], r["created_at"]
                if status and _touch_status:
                    await cur.execute("UPDATE sos_events SET status=%s WHERE id=%s", (status, sos_id))
            await conn.commit()
    else:
        update["id"] = len(_SOS_UPDATES) + 1
        update["created_at"] = _now_iso()
        _SOS_UPDATES.append(update)
        if status and _touch_status:
            for r in _SOS:
                if r["id"] == sos_id:
                    r["status"] = status
    return update


async def set_sos_status(sos_id: str, status: str) -> bool:
    """Back-compat thin wrapper — advances status and logs it to the timeline."""
    return await add_sos_update(sos_id, status=status, actor="officer") is not None


async def sos_detail(sos_id: str) -> dict | None:
    """Full incident view for the officer console: the SOS, the reporter's
    registration (who they are, contacts, medical flags), and the timeline."""
    sos = await get_sos(sos_id)
    if sos is None:
        return None
    reporter = None
    if sos.get("yatra_id"):
        reporter = await get_registration_by_id(sos["yatra_id"])
    if reporter is None and sos.get("user_id"):
        reporter = await get_registration_for_user(sos["user_id"])
    return {**sos, "reporter": reporter, "timeline": await list_sos_updates(sos_id)}


# ── checkpoint scans → crowd occupancy heatmap ──────────────────────
async def record_scan(checkpoint_id: str, *, yatra: str | None = None,
                      yatra_id: str | None = None, user_id: str | None = None) -> None:
    """Log one pass scan at a gate/halt/ghat. Aggregated into occupancy; we never
    store where anyone is BETWEEN checkpoints."""
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO checkpoint_scans(checkpoint_id,yatra,yatra_id,user_id) "
                    "VALUES(%s,%s,%s,%s)",
                    (checkpoint_id, yatra, yatra_id, user_id))
            await conn.commit()
    else:
        _SCANS.append({"checkpoint_id": checkpoint_id, "yatra": yatra,
                       "yatra_id": yatra_id, "user_id": user_id,
                       "created_at": datetime.now(timezone.utc)})


def _load_checkpoints(yatra: str | None):
    from agent.seed import load
    try:
        data = load("checkpoints")
    except Exception:
        return []
    return data.get(yatra or "", []) if yatra else [c for v in data.values() for c in v]


def _scan_status(load_pct: float) -> str:
    if load_pct >= 1.0:
        return "over"
    if load_pct >= 0.7:
        return "busy"
    return "ok"


async def checkpoint_occupancy(yatra: str | None = None, window_min: int = 30) -> dict:
    """Live crowd picture for the control room: recent scan counts per checkpoint
    vs its comfortable capacity (→ ok / busy / over), plus open-SOS hotspots
    mapped to the nearest checkpoint. First-party, no GPS, no per-person tracking."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_min)
    checkpoints = _load_checkpoints(yatra)

    # Recent scan counts per checkpoint.
    counts: dict[str, int] = {}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT checkpoint_id, COUNT(*) AS n FROM checkpoint_scans "
                    "WHERE created_at >= %s GROUP BY checkpoint_id", (cutoff,))
                for r in await cur.fetchall():
                    counts[r["checkpoint_id"]] = r["n"]
    else:
        for s in _SCANS:
            if s["created_at"] >= cutoff:
                counts[s["checkpoint_id"]] = counts.get(s["checkpoint_id"], 0) + 1

    # Open-SOS hotspots → nearest checkpoint (SOS carries coordinates).
    open_sos = [s for s in await list_sos() if (s.get("status") or "open") != "resolved"]
    incidents: dict[str, int] = {}
    for s in open_sos:
        if isinstance(s.get("lat"), (int, float)) and checkpoints:
            nearest = min(checkpoints, key=lambda c: _haversine_km(s["lat"], s["lng"], c["lat"], c["lng"]))
            incidents[nearest["id"]] = incidents.get(nearest["id"], 0) + 1

    rows, alerts = [], []
    for c in checkpoints:
        cap = c.get("capacity") or 500
        n = counts.get(c["id"], 0)
        load_pct = round(n / cap, 2)
        status = _scan_status(load_pct)
        row = {**c, "count": n, "load": load_pct, "status": status,
               "incidents": incidents.get(c["id"], 0)}
        rows.append(row)
        if status == "over":
            alerts.append({"id": c["id"], "name": c["name"], "count": n, "capacity": cap})

    lf = [x for x in await list_lost_found() if (x.get("status") or "open") != "reunited"]
    grv = [x for x in await list_grievances() if (x.get("status") or "open") != "resolved"]
    rows.sort(key=lambda r: r["load"], reverse=True)
    return {
        "window_min": window_min,
        "generated_at": _now_iso(),
        "checkpoints": rows,
        "alerts": alerts,
        "totals": {"scans": sum(counts.values()), "over": len(alerts),
                   "open_sos": len(open_sos), "open_lostfound": len(lf),
                   "open_grievances": len(grv)},
    }


async def officer_summary() -> dict:
    """Aggregate KPIs for the officer war-room: pilgrim headcount (rows, one per
    person), distinct families, and open SOS / lost-&-found counts."""
    regs = await list_registrations()
    sos = await list_sos()
    lf = await list_lost_found()
    grv = await list_grievances()
    by_yatra: dict[str, int] = {}
    families = set()
    for r in regs:
        by_yatra[r.get("yatra", "unknown")] = by_yatra.get(r.get("yatra", "unknown"), 0) + 1
        if r.get("group_id"):
            families.add(r["group_id"])
    return {
        "pilgrims": len(regs),
        "families": len(families),
        "by_yatra": by_yatra,
        "open_sos": sum(1 for s in sos if (s.get("status") or "open") == "open"),
        "open_lostfound": sum(1 for x in lf if (x.get("status") or "open") == "open"),
        "open_grievances": sum(1 for g in grv if (g.get("status") or "open") != "resolved"),
    }


# ── lost_found ──────────────────────────────────────────────────────
async def create_lost_found(*, kind: str, name: str, description: str, last_seen: str,
                            reporter_name: str, reporter_phone: str,
                            yatra: str | None = None, yatra_id: str | None = None) -> str:
    lid = f"LF-{_today()}-{_next():04d}"
    row = {"id": lid, "kind": kind, "status": "open", "name": name, "description": description,
           "last_seen": last_seen, "reporter_name": reporter_name, "reporter_phone": reporter_phone,
           "yatra": yatra, "yatra_id": yatra_id}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO lost_found(id,kind,status,name,description,last_seen,"
                    "reporter_name,reporter_phone,yatra,yatra_id) "
                    "VALUES(%(id)s,%(kind)s,%(status)s,%(name)s,%(description)s,%(last_seen)s,"
                    "%(reporter_name)s,%(reporter_phone)s,%(yatra)s,%(yatra_id)s)",
                    row,
                )
            await conn.commit()
    else:
        _LOSTFOUND.append(row)
    return lid


async def list_lost_found(yatra: str | None = None) -> list[dict]:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                if yatra:
                    await cur.execute("SELECT * FROM lost_found WHERE yatra=%s ORDER BY created_at DESC", (yatra,))
                else:
                    await cur.execute("SELECT * FROM lost_found ORDER BY created_at DESC")
                return [dict(r) for r in await cur.fetchall()]
    rows = [r for r in _LOSTFOUND if (not yatra or r.get("yatra") == yatra)]
    return list(reversed(rows))


async def set_lost_found_status(lid: str, status: str) -> bool:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE lost_found SET status=%s WHERE id=%s", (status, lid))
                changed = cur.rowcount
            await conn.commit()
            return bool(changed)
    for r in _LOSTFOUND:
        if r["id"] == lid:
            r["status"] = status
            return True
    return False


# ── grievances (pilgrim complaints) ─────────────────────────────────
async def create_grievance(*, category: str, description: str, location: str,
                           reporter_name: str, reporter_phone: str,
                           yatra: str | None = None, yatra_id: str | None = None) -> str:
    gid = f"GRV-{_today()}-{_next():04d}"
    row = {"id": gid, "category": category, "description": description, "location": location,
           "reporter_name": reporter_name, "reporter_phone": reporter_phone,
           "yatra": yatra, "yatra_id": yatra_id, "status": "open"}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO grievances(id,category,description,location,reporter_name,"
                    "reporter_phone,yatra,yatra_id,status) VALUES(%(id)s,%(category)s,%(description)s,"
                    "%(location)s,%(reporter_name)s,%(reporter_phone)s,%(yatra)s,%(yatra_id)s,%(status)s)",
                    row,
                )
            await conn.commit()
    else:
        _GRIEVANCES.append(row)
    return gid


async def list_grievances(yatra: str | None = None) -> list[dict]:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                if yatra:
                    await cur.execute("SELECT * FROM grievances WHERE yatra=%s ORDER BY created_at DESC", (yatra,))
                else:
                    await cur.execute("SELECT * FROM grievances ORDER BY created_at DESC")
                return [dict(r) for r in await cur.fetchall()]
    rows = [r for r in _GRIEVANCES if (not yatra or r.get("yatra") == yatra)]
    return list(reversed(rows))


async def set_grievance_status(gid: str, status: str) -> bool:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE grievances SET status=%s WHERE id=%s", (status, gid))
                changed = cur.rowcount
            await conn.commit()
            return bool(changed)
    for r in _GRIEVANCES:
        if r["id"] == gid:
            r["status"] = status
            return True
    return False


# ── alerts (officer → pilgrim broadcast) ────────────────────────────
async def create_alert(*, title: str, message: str, severity: str = "info",
                       yatra: str | None = None) -> str:
    aid = f"ALRT-{_today()}-{_next():04d}"
    row = {"id": aid, "title": title, "message": message, "severity": severity,
           "yatra": yatra, "active": True}
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO alerts(id,title,message,severity,yatra,active) "
                    "VALUES(%(id)s,%(title)s,%(message)s,%(severity)s,%(yatra)s,%(active)s)",
                    row,
                )
            await conn.commit()
    else:
        _ALERTS.append(row)
    return aid


async def list_alerts(yatra: str | None = None, active_only: bool = True) -> list[dict]:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM alerts ORDER BY created_at DESC")
                rows = [dict(r) for r in await cur.fetchall()]
    else:
        rows = list(reversed(_ALERTS))
    # Alerts with no yatra are broadcast to all; yatra filter keeps those + matches.
    if yatra:
        rows = [r for r in rows if not r.get("yatra") or r.get("yatra") == yatra]
    if active_only:
        rows = [r for r in rows if r.get("active", True)]
    return rows


async def set_alert_active(aid: str, active: bool) -> bool:
    pool = await _pool()
    if pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE alerts SET active=%s WHERE id=%s", (active, aid))
                changed = cur.rowcount
            await conn.commit()
            return bool(changed)
    for r in _ALERTS:
        if r["id"] == aid:
            r["active"] = active
            return True
    return False
