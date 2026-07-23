# Maharashtra Yatra Sahayak — SwiftChat Agent

Conversational pilgrim-safety agent for the **Pandharpur Wari** and **Simhastha Kumbh (Nashik)**, on ConveGenius SwiftChat. Mirrors the `swift-learning-agent` (Pravasi Setu) FastAPI + LangGraph pattern.

Covers the six NDMA pilgrim-app features — weather, travel advisories, logistics (pony/transport rates), helplines, emergency drills, and road signage — plus yatri registration with a QR yatra pass. Trilingual (Marathi / Hindi / English).

## Status

**Plan 1 (this repo state): backend foundation & agent spine — complete.**
A yatri bot that greets, selects language, selects yatra, and routes each turn through a LangGraph state machine (`content_policy → language_gate → yatra_context → intent_router → activity`). The seven activities are stubs; real behaviour, web apps, the officer war-room, and voice arrive in Plans 2–5.

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
