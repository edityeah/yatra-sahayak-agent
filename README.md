# Maharashtra Yatra Sahayak — SwiftChat Agent

Conversational pilgrim-safety agent for the **Pandharpur Wari** and **Simhastha Kumbh (Nashik)**, on ConveGenius SwiftChat. Mirrors the `swift-learning-agent` (Pravasi Setu) FastAPI + LangGraph pattern.

Covers the six NDMA pilgrim-app features — weather, travel advisories, logistics (pony/transport rates), helplines, emergency drills, and road signage — plus yatri registration with a QR yatra pass. Trilingual (Marathi / Hindi / English).

## Status

**Plans 1–2 complete: agent spine + real activities.**
A yatri bot that greets, selects language, selects yatra, and routes each turn through a LangGraph state machine (`content_policy → language_gate → yatra_context → intent_router → activity`). All seven activities are now real:
- **weather** — live IMD call (`IMD_API_URL`) with a cached fallback so the demo never dies
- **advisory** — district advisories, severity-ordered, from seed data
- **logistics** — indicative government-notified pony/transport rates
- **helpline** — one-tap `tel:` links (112 / 108 / control room / temple trust)
- **drills_sos** — preparedness drills, and a real SOS that records a `sos_event` and acknowledges calmly (trilingual even before a language is chosen); a first-turn SOS bypasses the language/yatra prompts
- **signage** — turn-by-turn guidance + a link to the (Plan 3) route-map web app
- **registration** — multi-turn simulated e-KYC (no real Aadhaar) issuing a Yatra ID + QR pass link

Seed content and cross-turn state (language, yatra, registration intake) are held server-side (`persistence` — Postgres when `DATABASE_URL` is set, in-memory otherwise).

**Plan 3 complete: yatri web apps + in-browser chat.**
A React + Vite SPA (`webview/`) served as SwiftChat BotExtension activities, plus a browser chat UI so the whole bot can be exercised **without a SwiftChat registration**. The agent exposes read-only `/api/*` JSON endpoints the SPA reads.
- **chat** (`/`) — streams the agent over `/messages`; the primary test surface
- **QR pass** (`/yatri/pass?id=`) — renders the registration + a scannable QR
- **route map** (`/yatri/map?yatra=`) — Leaflet + OpenStreetMap with geo-tagged halts/ghats/medical/water/toilet pins
- **logistics / drills / advisories** — live seed-backed lists, trilingual

**Plan 5 complete: voice.** A browser **Call** button (`/voice`) + a LiveKit + OpenAI Realtime voice worker (`agent/voice_agent.py`) — persona **Setu**, trilingual, SOS-first (a voice-raised emergency records a `sos_event` via `raise_sos`, same store as text SOS). Gated on LiveKit creds + a Realtime-enabled OpenAI key + a paid Render worker; see `docs/DEPLOY.md`. Degrades gracefully (503 → "voice not enabled") when unconfigured.

Deferred: officer war-room dashboard (later).

## Run the web app + chat locally
```bash
# terminal 1 — agent
cd agent && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
OPENAI_API_KEY=sk-... uvicorn webhook:app --port 8000

# terminal 2 — webview
cd webview && npm install && cp .env.example .env
npm run dev     # → http://localhost:5174
```
Open http://localhost:5174. Deploy (Render + Vercel): see `docs/DEPLOY.md`.

## Run the agent

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate   # Python >= 3.11
pip install -e ".[dev]"
cp .env.example .env    # set OPENAI_API_KEY
uvicorn webhook:app --port 8000 --reload
# → http://localhost:8000/health
```

DB is optional — leave `DATABASE_URL` empty to run in-memory.

## Test

```bash
pytest -q                # unit tests (offline — deterministic paths, no network)
bash scripts/smoke.sh    # end-to-end (needs a running agent + a real OPENAI_API_KEY)
```

## Architecture & plans

- Spec: `docs/superpowers/specs/2026-07-23-maharashtra-yatra-sahayak-poc-design.md`
- Plans: `docs/superpowers/plans/` — Plan 1 (foundation) is implemented; Plans 2–5 (activities, web apps, officer war-room, voice) follow.

The flow (spine):

```
content_policy ──blocked──► END (refusal)
   │ allowed / SOS-flag
language_gate  ──lang None──► END (language ask)
   │
yatra_context  ──yatra None──► END (yatra ask)
   │
intent_router ──► { weather | advisory | logistics | helpline | drills_sos | signage | registration } ──► END
              └─► browse | answer | off_topic ──► END
```
