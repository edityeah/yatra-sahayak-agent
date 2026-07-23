# Yatra Sahayak — Plan 2: Real Activities

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the seven stub activity nodes from Plan 1 with real behaviour — weather (live IMD + cached fallback), travel advisories, logistics (govt-notified rates), helplines (one-tap 112/108/control-room), emergency drills + live SOS, road signage, and yatri registration with a simulated-e-KYC QR yatra pass — for both Pandharpur Wari and Simhastha Kumbh, trilingual (mr/hi/en).

**Architecture:** Keep the Plan 1 spine unchanged (`content_policy → language_gate → yatra_context → intent_router → activity → END`). Add: (1) a `data/` seed layer + `seed.py` loader for all reference content; (2) a `persistence.py` layer that uses Postgres when `DB_ENABLED` and falls back to in-memory dicts otherwise (for `user_state`, `registrations`, `sos_events`); (3) an SOS-gate fix so an emergency bypasses the language/yatra prompts; (4) refactor `nodes/activities.py` into a `nodes/activities/` package, one focused module per activity. Activities emit trilingual markdown replies (text SSE, as in Plan 1); rich map/QR visuals belong to the Plan 3 web apps.

**Tech Stack:** unchanged (Python 3.11+/3.14 · FastAPI · LangGraph · OpenAI gpt-4o-mini · psycopg · httpx for IMD) + `qrcode`/image only later (Plan 3 web app renders the QR; Plan 2 issues the Yatra ID + pass link).

**Base:** branch `feat/plan-02-activities` off Plan 1. Reference clone at `…/scratchpad/swift-learning-agent` (see `nodes/grievance_officer.py` for the multi-turn intake state-machine pattern reused by `registration`). Spec: `docs/superpowers/specs/2026-07-23-maharashtra-yatra-sahayak-poc-design.md` §5–§7.

---

## File Structure

```
data/                                  # NEW — seed content (JSON), trilingual user-facing strings
├── yatras.json                        # 2 yatras: names, control-room, districts
├── routes.json                        # halts/ghats/POIs per yatra
├── logistics_rates.json               # govt-notified pony/palkhi/porter/transport rates
├── helplines.json                     # 112/108/control-room/temple-trust per yatra
├── advisories.json                    # sample district advisories per yatra
├── signage.json                       # corridor signage + turn-by-turn per yatra
├── drills.json                        # preparedness modules (trilingual title+script)
└── weather_fallback.json              # cached IMD-style route forecast per yatra

agent/agent/
├── seed.py                            # NEW — cached JSON loader (load(name) -> dict)
├── persistence.py                     # NEW — user_state / registrations / sos_events (DB or memory)
├── weather_client.py                  # NEW — IMD httpx call + fallback to weather_fallback.json
├── db.py                              # MODIFY — extend MIGRATIONS_SQL (registrations, sos_events, user_state cols)
├── state.py                           # MODIFY — add registration-intake fields
├── graph.py                           # MODIFY — SOS bypass of language/yatra gates
├── webhook.py                         # MODIFY — persistence-backed session (DB when enabled)
└── nodes/
    ├── activities/                    # NEW package (replaces activities.py)
    │   ├── __init__.py                # ACTIVITY_NODES = {..7 real nodes..}
    │   ├── weather.py
    │   ├── advisory.py
    │   ├── logistics.py
    │   ├── helpline.py
    │   ├── drills_sos.py
    │   ├── signage.py
    │   └── registration.py
    └── (spine nodes unchanged)
tests/
├── test_seed.py · test_persistence.py · test_weather.py · test_logistics.py
├── test_helpline.py · test_advisory.py · test_signage.py · test_drills_sos.py
├── test_registration.py · test_sos_gate.py
```

**Node contract (all activities):** `async def <name>(state: YatraState) -> YatraState`. Read `state["language"]` (`mr|hi|en`, default `en`) and `state["active_yatra"]` (`pandharpur|kumbh`, default `pandharpur`). Append exactly one `AIMessage` with a trilingual markdown reply built from seed/live data. Set `current_node`. Deterministic where possible (no LLM) so tests run offline; only `registration` and `drills_sos` free-text summarisation may call the LLM, and must fall back gracefully when the key/LLM is unavailable.

---

## Task 1: Seed data layer

**Files:** Create `data/*.json` (8 files), `agent/agent/seed.py`, `tests/test_seed.py`.

- [ ] **Step 1: Write `tests/test_seed.py`** (failing)

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import seed


def test_yatras_has_both():
    y = seed.load("yatras")
    assert set(y.keys()) == {"pandharpur", "kumbh"}
    assert y["pandharpur"]["name"]["mr"]        # trilingual name present
    assert y["kumbh"]["control_room"]


def test_logistics_rates_per_yatra():
    r = seed.load("logistics_rates")
    assert r["pandharpur"] and r["kumbh"]
    # each entry has a service + notified rate
    first = r["pandharpur"][0]
    assert "service" in first and "rate" in first


def test_missing_file_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        seed.load("does-not-exist")
```

- [ ] **Step 2: Create `agent/agent/seed.py`**

```python
"""Seed-data loader — reads reference JSON from DATA_DIR, cached per name.
All user-facing strings are trilingual dicts {"mr":.., "hi":.., "en":..}."""
from __future__ import annotations
import json
import os
from functools import lru_cache

from agent.config import get_settings


@lru_cache(maxsize=None)
def load(name: str) -> dict | list:
    path = os.path.join(get_settings().DATA_DIR, f"{name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"seed file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def t(value, lang: str) -> str:
    """Resolve a trilingual dict (or plain string) to the chosen language."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or next(iter(value.values()), "")
    return str(value)
```

- [ ] **Step 3: Author the 8 JSON files** under `data/`. Content must be realistic for the two yatras and trilingual for user-facing text. Minimum shape per file (author fuller content, but at least this):

`data/yatras.json`
```json
{
  "pandharpur": {
    "name": {"mr": "पंढरपूर वारी", "hi": "पंढरपुर वारी", "en": "Pandharpur Wari"},
    "control_room": "020-1234-5678",
    "districts": ["Pune", "Solapur"]
  },
  "kumbh": {
    "name": {"mr": "सिंहस्थ कुंभमेळा (नाशिक)", "hi": "सिंहस्थ कुंभ (नासिक)", "en": "Simhastha Kumbh (Nashik)"},
    "control_room": "0253-1234-567",
    "districts": ["Nashik"]
  }
}
```

`data/logistics_rates.json` — per yatra, a list of `{service:{mr,hi,en}, rate (INR str), unit:{...}, note?}`. Use plausible published-style numbers (e.g. Wari palkhi transport, bullock cart; Kumbh shared vehicle, porter). Mark clearly as government-notified rates.

`data/helplines.json` — per yatra a list of `{label:{mr,hi,en}, number, dial}` including 112 (emergency), 108 (ambulance), the yatra control room, and the temple trust. `dial` is the raw number for a `tel:` link.

`data/routes.json` — per yatra a list of halts/ghats `{name:{...}, kind: "night_halt|ghat|medical|water|toilet", note?}`.

`data/advisories.json` — per yatra a list of `{title:{...}, body:{...}, severity: "info|warning|critical", issued_by}`.

`data/signage.json` — per yatra a list of corridor points `{at:{...}, guidance:{...}}` for turn-by-turn text.

`data/drills.json` — a list (shared) of `{id, title:{...}, body:{...}}` for stampede, ghat/riverbank safety, first aid, heat illness, missing-person.

`data/weather_fallback.json` — per yatra `{summary:{...}, temp_c, rain_alert:{...}|null, updated: "cached"}`.

- [ ] **Step 4: Run** `pytest tests/test_seed.py -v` → 3 pass. Then `pytest -q` → full suite still green.
- [ ] **Step 5: Commit** `feat(data): seed layer for yatras/rates/helplines/advisories/signage/drills/weather`

---

## Task 2: Persistence layer (DB-or-memory)

**Files:** Create `agent/agent/persistence.py`, `tests/test_persistence.py`; Modify `agent/agent/db.py` (extend `MIGRATIONS_SQL`).

Provides async `user_state` (language, active_yatra), `registrations`, and `sos_events` access. Uses Postgres when `settings.DB_ENABLED`, else module-level in-memory dicts. All functions are async and safe to call with DB off.

- [ ] **Step 1: Extend `MIGRATIONS_SQL` in `db.py`** — add (idempotent):
```sql
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
```
(`user_state` table already exists from Plan 1.)

- [ ] **Step 2: Write `tests/test_persistence.py`** (failing) — exercises the in-memory path (DB off):
```python
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import persistence as p


def test_user_state_roundtrip_memory():
    async def go():
        await p.set_user_state("u1", language="mr", active_yatra="kumbh")
        s = await p.get_user_state("u1")
        assert s["language"] == "mr" and s["active_yatra"] == "kumbh"
    asyncio.run(go())


def test_registration_and_sos_memory():
    async def go():
        yid = await p.create_registration("u1", yatra="pandharpur", name="Asha", phone="+9199...", group_name="Dindi 5", emergency_contact="+9198...", medical_flags="elderly")
        assert yid.startswith("PWARI-") or yid.startswith("KUMBH-")
        reg = await p.get_registration_for_user("u1")
        assert reg["name"] == "Asha"
        sid = await p.create_sos("u1", yatra="pandharpur", yatra_id=yid, location="Wakhari halt", nature="medical")
        assert sid
        events = await p.list_sos()
        assert any(e["id"] == sid for e in events)
    asyncio.run(go())
```

- [ ] **Step 3: Create `agent/agent/persistence.py`** — async interface with DB + in-memory branches. In-memory dicts: `_USER_STATE`, `_REGISTRATIONS`, `_SOS`. Yatra-id format: `PWARI-YYYYMMDD-NNNN` / `KUMBH-YYYYMMDD-NNNN` (date passed in / counter-based; since `Date.now()` is fine in the running app but tests must be deterministic, derive the sequence from a module counter and accept an optional `today` arg defaulting to `datetime.now`). Functions: `get_user_state(user_id)`, `set_user_state(user_id, *, language=None, active_yatra=None)`, `create_registration(...) -> yatra_id`, `get_registration_for_user(user_id)`, `create_sos(...) -> id`, `list_sos()`. When `DB_ENABLED`, use `db.get_pool()`; else the dicts. Provide `reset()` for tests.

- [ ] **Step 4: Run** `pytest tests/test_persistence.py -v` → pass. Full suite green.
- [ ] **Step 5: Commit** `feat(agent): persistence layer (user_state/registrations/sos, DB-or-memory)`

---

## Task 3: Wire persistence into the webhook + SOS-gate fix

**Files:** Modify `agent/webhook.py`, `agent/agent/graph.py`, `tests/test_sos_gate.py`.

- [ ] **Step 1: SOS-gate fix in `graph.py`** — change `_after_policy` so an emergency skips the language/yatra prompts:
```python
def _after_policy(state: YatraState):
    if state.get("policy_result") == "blocked":
        return END
    if state.get("sos"):
        return "intent_router"   # emergency: skip language/yatra gates
    return "language_gate"
```
`intent_router` already routes `sos → drills_sos` before the LLM, and `drills_sos` must handle `language=None`/`active_yatra=None` (default to a trilingual SOS acknowledgement — see Task 9).

- [ ] **Step 2: Webhook uses persistence for language/yatra** — in `_stream_turn`, after building `state["messages"]`, replace the `session_store` language/yatra load/save with `persistence.get_user_state(user_id)` / `set_user_state(...)`. Keep `session_store` for the transcript only (DB transcript is out of scope here). So: transcript ← session_store; language/active_yatra ← persistence (DB when enabled, memory otherwise). Persist both after invoke.

- [ ] **Step 3: Write `tests/test_sos_gate.py`** — a first-turn SOS reaches `drills_sos`, not the language ask:
```python
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent.graph import yatra_graph


def test_first_turn_sos_reaches_drills_sos():
    s = new_state("sess", "user")
    s["messages"] = [HumanMessage(content="emergency stampede help")]
    out = asyncio.run(yatra_graph.ainvoke(s))
    assert out["current_node"] == "drills_sos"
    assert "choose your language" not in out["messages"][-1].content
```

- [ ] **Step 4: Run** `pytest tests/test_sos_gate.py -v` + full suite. (The Plan 1 multi-turn webhook test must still pass — persistence memory path replaces the store for language/yatra; update that test only if the swap changes an assertion, keeping its intent.)
- [ ] **Step 5: Commit** `feat(agent): SOS bypasses language/yatra gates; webhook uses persistence`

---

## Task 4: Refactor `activities.py` → `activities/` package

**Files:** Delete `agent/agent/nodes/activities.py`; Create `agent/agent/nodes/activities/__init__.py`; keep the seven stub bodies temporarily as thin modules so the graph/tests stay green, then Tasks 5–11 replace each.

- [ ] **Step 1:** Create `nodes/activities/__init__.py` that imports the seven node functions from their modules and assembles `ACTIVITY_NODES = {"weather": weather, ...}`. Create each `nodes/activities/<name>.py` with the Plan-1 stub body for now (`async def <name>(state)` appending the stub text). Delete `nodes/activities.py`.
- [ ] **Step 2:** `graph.py` already does `from agent.nodes.activities import ACTIVITY_NODES` — unchanged. Run full suite → still 31-ish green (activity stub test still passes; it imports `ACTIVITY_NODES`).
- [ ] **Step 3: Commit** `refactor(agent): split activities into a focused package`

---

## Tasks 5–11: the seven real activity nodes

Each task: write a failing test asserting the real reply contains the right seed/live content in the active language; implement the node reading `seed`/`persistence`/`weather_client`; keep it deterministic/offline where possible; run; commit. All replace the stub in `nodes/activities/<name>.py`.

### Task 5: `helpline.py`
Reply lists 112 / 108 / control-room / temple-trust from `seed.load("helplines")[yatra]`, in `state["language"]`, each as a markdown `tel:` link + a `buttons` rich block appended for SwiftChat one-tap. Test: reply contains `112`, `108`, and a `tel:` link; Marathi labels when `language=="mr"`. Deterministic.

### Task 6: `logistics.py`
Reply renders the govt-notified rate table from `seed.load("logistics_rates")[yatra]` in the active language, with an "overcharge? report it" line. Test: reply contains a service name + its rate for the active yatra; switches content between pandharpur/kumbh. Deterministic.

### Task 7: `advisory.py`
Reply lists current advisories from `seed.load("advisories")[yatra]` (title + body, severity-ordered critical→info) in the active language. Test: reply contains a seeded advisory title; ordering puts a `critical` first. Deterministic.

### Task 8: `signage.py`
Reply gives turn-by-turn guidance from `seed.load("signage")[yatra]` in the active language + a link to the (Plan 3) route-map web app (`{PUBLIC_WEBVIEW_BASE}/yatri/map?yatra=<yatra>`). Test: reply contains a seeded guidance string + the map link. Deterministic.

### Task 9: `drills_sos.py`
Two behaviours in one node, branch on `state["sos"]`:
- **SOS** (`state["sos"]` true): create a `sos_events` row via `persistence.create_sos(user_id, yatra, yatra_id (from registration if any), location=<parsed-or-unknown>, nature=<parsed-or-unknown>)`; reply with a calm trilingual acknowledgement including the control-room number (from `seed yatras[yatra].control_room`, or a generic 112 line if yatra unknown), the fact that the control room has been alerted, and one-tap 112. Must work with `language=None` (emit a compact mr+hi+en SOS ack) and `active_yatra=None`.
- **drills** (not SOS): list preparedness modules from `seed.load("drills")` (title + one-line body) in the active language.
Tests: (a) SOS path creates an sos_event (check `persistence.list_sos()` grew) and reply mentions 112/alerted; (b) drills path lists a seeded module title. Both offline (no LLM; location/nature parsing is best-effort keyword extraction, not an LLM call — keep deterministic).

### Task 10: `weather.py` + `weather_client.py`
`weather_client.get_forecast(yatra)` tries a live IMD call (httpx GET to `settings.IMD_API_URL` templated per yatra, short timeout) and on ANY error/absence falls back to `seed.load("weather_fallback")[yatra]`, tagging the result `source: "live"|"cached"`. Add `IMD_API_URL` (default empty ⇒ always fallback) to `config.py`. `weather.py` renders the forecast (summary, temp, rain/heat alert) in the active language and notes the source. Tests (offline, `IMD_API_URL` empty): reply contains the cached summary for the active yatra and is labelled cached; a rain alert present in seed shows up. Add `IMD_API_URL` to `.env.example`.

### Task 11: `registration.py` (multi-turn intake + QR pass)
Model on the reference `grievance_officer.py` multi-turn state machine. Add intake fields to `state.py` (`reg_stage`, `reg_fields`). Flow: intake → collect (name → phone → group/Dindi → emergency contact → medical flags, simulated e-KYC, NO real Aadhaar) → confirm → issue. On issue: `persistence.create_registration(...)` → Yatra ID; reply with the ID, a "pass ready" message, and a link to the pass web app (`{PUBLIC_WEBVIEW_BASE}/yatri/pass?id=<yatra_id>`) where the QR renders (Plan 3). Persist intake progress across turns via the session/persistence store keyed by conversation. Tests: drive the intake to completion and assert a Yatra ID is issued + a registration row exists; assert the e-KYC step never asks for a real Aadhaar number (copy check). The stage machine is deterministic; any free-text field summarisation must degrade gracefully without the LLM.

Each of Tasks 5–11 ends with: run the node's test + full suite green, then commit `feat(agent): real <name> activity`.

---

## Task 12: Integration + smoke update

**Files:** Modify `scripts/smoke.sh` (add per-activity turns), `README.md` (mark Plan 2 done), add `tests/test_activities_integration.py`.

- [ ] End-to-end offline test: for each activity intent, drive the graph with language+yatra pre-set and assert the real (non-stub) reply. SOS via the tripwire; others by setting `state["intent"]` is not possible (router needs LLM) — instead call each activity node directly with a prepared state (the nodes are the unit under test; the router→node wiring is already covered by graph tests). Assert none of the replies still contain the `— Plan 2.` stub text.
- [ ] Update `scripts/smoke.sh` to exercise weather, logistics, helpline, registration, SOS across a multi-turn conversation.
- [ ] Update `README.md`: Plan 2 complete; activities real; note IMD live-with-fallback + simulated e-KYC.
- [ ] Commit `test(agent): activity integration + smoke/readme for Plan 2`.

---

## Self-Review

**Spec coverage:** §5 all seven activities → Tasks 5–11; QR pass + simulated e-KYC → Task 11; SOS + sos_events → Tasks 2/3/9; §6 fidelity (live IMD + fallback; canned rates/advisories/signage/drills; real tel: dial) → Tasks 5/6/7/8/10; §7 trilingual → every node reads `state["language"]` via `seed.t`; DB-backed user_state → Tasks 2/3; first-turn-SOS refinement → Task 3.

**Deferred (correct, not gaps):** rich map/QR *visuals* and the control-room dashboard that consumes `sos_events`/`registrations` → Plans 3–4; voice → Plan 5.

**Placeholder scan:** the per-activity specs (Tasks 5–8) describe seed shape + reply content + test assertions precisely rather than pasting near-identical node bodies; the implementer builds each from the stated contract + the `seed`/`persistence`/`weather_client` APIs defined in Tasks 1–2/10. Foundation tasks (1–3, 9–11) carry full code or exact schemas.

**Type/name consistency:** `seed.load`/`seed.t`, `persistence.{get_user_state,set_user_state,create_registration,get_registration_for_user,create_sos,list_sos,reset}`, `weather_client.get_forecast`, `ACTIVITY_NODES` keys (unchanged 7) all referenced identically across tasks and match the graph/router from Plan 1.
