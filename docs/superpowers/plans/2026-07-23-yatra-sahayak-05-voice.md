# Yatra Sahayak — Plan 5: Voice (yatri)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Voice can't be unit-tested offline (needs LiveKit + OpenAI Realtime); verification = the token/SOS endpoints get pytest coverage, the worker + call UI are build/import-verified, and a LIVE call is checked once ConveGenius LiveKit creds + a Realtime-enabled key are in place. Steps use `- [ ]`.

**Goal:** A voice surface for the yatri: a LiveKit + OpenAI Realtime **voice worker** (Yatra persona, trilingual, with a `raise_sos` tool and weather/helpline tools), plus a **browser "Call" button** in the webview (LiveKit JS) so voice is testable in a browser without SwiftChat. A voice-raised SOS lands in the SAME `sos_events` store as text SOS (so the future control-room dashboard sees both).

**Architecture (mirrors `swift-learning-agent/agent/voice_agent.py`):** A separate Render **worker** process runs `agent/voice_agent.py` (LiveKit Agents 1.6 + `openai.realtime.RealtimeModel`, `gpt-realtime`, `semantic_vad`), registered under `AGENT_NAME` (explicit dispatch). The **web service** gains a `/api/voice/token` endpoint that mints a LiveKit join token AND creates an explicit agent dispatch for a fresh room, and a `/api/voice/sos` endpoint the worker's `raise_sos` tool calls over HTTP (so the worker needs no DB — same boundary as the reference). The **webview** adds a Call page using `livekit-client`: get token → join room → publish mic → play the agent's audio.

**Tech Stack additions:** agent → `livekit-agents~=1.6`, `livekit-plugins-openai~=1.6`, `livekit-api` (token mint + dispatch); webview → `livekit-client`. OpenAI Realtime access required on the key.

**Base:** branch `feat/plan-05-voice` off `main` (Plans 1–3 merged). Reference: `…/scratchpad/swift-learning-agent/agent/voice_agent.py` + `agent/agent/voice/tools.py` (read them).

**Prerequisites (user-provided at deploy):** `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` (ConveGenius's project), an `OPENAI_API_KEY` with Realtime access, and a Render **paid worker** plan.

---

## File Structure
```
agent/
├── pyproject.toml                 # + livekit-agents, livekit-plugins-openai, livekit-api
├── agent/config.py                # + LIVEKIT_URL/KEY/SECRET, AGENT_NAME (defaults)
├── agent/voice_agent.py           # NEW — LiveKit worker (Yatra persona + tools)
├── agent/voice/
│   ├── __init__.py
│   ├── persona.py                 # trilingual Yatra voice instructions + greeting
│   └── tools.py                   # raise_sos (HTTP→web), get_weather, get_helplines
├── webhook.py                     # + POST /api/voice/token, POST /api/voice/sos
tests/test_voice_endpoints.py      # NEW — token + sos endpoint tests (offline)

webview/
├── package.json                   # + livekit-client
└── src/
    ├── voice/CallPage.jsx          # NEW — Call button + in-call UI
    └── lib/api.js                  # + getVoiceToken()
    (AppShell nav gains a "Call" entry; App.jsx route /voice)

render.yaml                        # + worker service (plan: starter) for voice
docs/DEPLOY.md                     # + voice section (LiveKit creds, worker plan, Realtime)
```

---

## Task V1: web-service voice endpoints + config + deps

**Files:** `agent/pyproject.toml`, `agent/agent/config.py`, `agent/webhook.py`, `tests/test_voice_endpoints.py`.

- Add deps to `pyproject.toml`: `livekit-agents~=1.6`, `livekit-plugins-openai~=1.6`, `livekit-api>=0.8`. (These are heavy; `pip install` in the venv may take a while.)
- `config.py`: add `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (all default ""), `AGENT_NAME` (default `"yatra-sahayak-voice"`), `VOICE_ENABLED` = bool(all three LiveKit vars set).
- `webhook.py`:
  - `POST /api/voice/token` (X-API-Key) — body `{user_id, yatra?, language?}`. If `not VOICE_ENABLED` → 503 `{"error":"voice not configured"}`. Else: build a room `f"yatra-voice-{user_id}-{short-uuid}"`; mint a join token with `livekit.api.AccessToken(key, secret).with_identity(user_id).with_grants(VideoGrants(room_join=True, room=room))`; create an explicit dispatch `livekit.api.LiveKitAPI(url,key,secret).agent_dispatch.create_dispatch(CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=room, metadata=json.dumps({user_id,yatra,language})))`; return `{url: LIVEKIT_URL, token, room}`. Wrap dispatch in try/except (if the worker isn't up yet, still return the token so the client can connect; log the error).
  - `POST /api/voice/sos` (X-API-Key) — body `{user_id, nature?, location?, yatra?, yatra_id?}` → `await persistence.create_sos(...)` → `{sos_id}`. This is what the worker's `raise_sos` tool calls, so a voice SOS shares the text SOS store.
- `tests/test_voice_endpoints.py`: `/api/voice/token` → 503 when VOICE not configured (default in tests, no LiveKit env) AND 401 without key; `/api/voice/sos` with key creates an sos_event (check `persistence.list_sos()` grew); without key → 401.

Steps: write failing tests → implement → `pytest -q` green → commit `feat(agent): voice token + sos endpoints (LiveKit dispatch)`.

## Task V2: voice worker (persona + tools) + render worker service

**Files:** `agent/agent/voice/{__init__,persona,tools}.py`, `agent/voice_agent.py`, `render.yaml`.

- `voice/persona.py`: `INSTRUCTIONS` — Yatra Sahayak voice persona: warm public-safety-helpline tone; **trilingual** (detect & mirror Marathi/Hindi/English; default Marathi); scope = the six NDMA activities (weather, advisories, transport/pony rates, helplines, drills, signage) + registration; **SOS-first**: if the caller reports an emergency (stampede, medical, drowning, missing person, accident), calmly reassure, call `raise_sos`, then tell them the control room is alerted + to call 112; short spoken replies, no URLs/markdown; honesty rules; refuse terrorism/self-harm cleanly (self-harm → KIRAN 1800-599-0019). Plus `GREETING` (one-line trilingual-capable opener). Mirror the reference's structure, Yatra content.
- `voice/tools.py` (mirror reference `_worker_id_from_ctx` + `@function_tool`):
  - `raise_sos(context, nature, location=None)` → POST to `AGENT_API_HOST/api/voice/sos` (httpx, X-API-Key=`AGENT_API_KEY`) with `{user_id (from job metadata), nature, location, yatra (from metadata)}`; return a spoken instruction ("SOS sent, tell them help is coming + call 112"). Never DB-direct.
  - `get_weather(context)` → call `weather_client.get_forecast(yatra)` directly (pure seed/httpx, no DB) → spoken summary.
  - `get_helplines(context)` → `seed.load("helplines")[yatra]` → spoken 112/108/control-room.
  - `ALL_TOOLS = [raise_sos, get_weather, get_helplines]`.
- `voice_agent.py`: mirror the reference — `JobMetadata` (user_id/yatra/language), `YatraVoiceAssistant(Agent)` with `on_enter` greeting, `entrypoint` building `AgentSession(llm=openai.realtime.RealtimeModel(model="gpt-realtime", voice="alloy", modalities=["audio"], turn_detection=semantic_vad))`, `WorkerOptions(agent_name=settings.AGENT_NAME, num_idle_processes=0, ws_url/api_key/api_secret from settings)`. Lazy-import tools. Drop the transcript-summary shutdown (out of scope) OR keep a minimal logger.
- `render.yaml`: add a second service:
  ```yaml
  - type: worker
    name: yatra-sahayak-voice
    runtime: python
    plan: starter
    rootDir: agent
    buildCommand: pip install --upgrade pip && pip install .
    startCommand: python voice_agent.py start
    envVars:
      - {key: PYTHON_VERSION, value: 3.11.9}
      - {key: OPENAI_API_KEY, sync: false}      # Realtime-enabled
      - {key: LIVEKIT_URL, sync: false}
      - {key: LIVEKIT_API_KEY, sync: false}
      - {key: LIVEKIT_API_SECRET, sync: false}
      - {key: AGENT_NAME, value: yatra-sahayak-voice}
      - {key: AGENT_API_HOST, sync: false}       # the web service URL
      - {key: AGENT_API_KEY, sync: false}        # = web INTERNAL_API_KEY
  ```
  Also add `LIVEKIT_*` (sync:false) + `AGENT_NAME` to the WEB service envVars (it needs them to mint tokens + dispatch).
- Verify: `python -c "import agent.voice_agent"` imports without error (deps installed); `python -c "from agent.voice.tools import ALL_TOOLS; print(len(ALL_TOOLS))"` → 3. No live call in this task.
- Commit `feat(agent): LiveKit voice worker (Yatra persona + raise_sos/weather/helpline tools)`.

## Task V3: browser Call button (LiveKit JS)

**Files:** `webview/package.json` (+`livekit-client`), `webview/src/lib/api.js` (+`getVoiceToken`), `webview/src/voice/CallPage.jsx`, `webview/src/App.jsx` (+`/voice` route), `webview/src/components/AppShell.jsx` (+"Call" nav), `webview/src/strings.js` (+labels).
- `getVoiceToken({user_id, yatra, language})` → `apiGet`-style POST to `/api/voice/token` → `{url, token, room}`.
- `CallPage.jsx`: a big **Call** button. On click: `getVoiceToken()`; `const room = new Room(); await room.connect(url, token); await room.localParticipant.setMicrophoneEnabled(true);` subscribe to remote audio tracks → attach to a hidden `<audio autoplay>`; show in-call UI (status: connecting/connected, a mute toggle, a **Hang up** that `room.disconnect()`). Handle the 503 "voice not configured" gracefully with a friendly "voice isn't enabled on this deployment yet" note. Request mic permission; show an error if denied.
- Trilingual labels via `useLang()`.
- `npm run build` passes. Commit `feat(webview): browser Call button (LiveKit voice client)`.

## Task V4: deploy docs + verification checklist

**Files:** `docs/DEPLOY.md` (voice section), `README.md`.
- DEPLOY.md: add a "Voice (optional)" section — provide `LIVEKIT_URL/KEY/SECRET` (ConveGenius project) on BOTH the web service and the worker; ensure the web service's `PUBLIC_WEBVIEW_BASE` and the worker's `AGENT_API_HOST` (= web service URL) + `AGENT_API_KEY` (= web `INTERNAL_API_KEY`) are set; the OpenAI key must have Realtime access; the worker needs a paid plan. Live-test checklist: open `/voice`, tap Call, grant mic, hear the greeting, say "emergency stampede" → confirm an `sos_event` (persistence) and the spoken ack.
- README: note voice = Plan 5 done (browser Call + worker), gated on LiveKit creds + Realtime.
- Commit `docs: voice deploy + verification`.

---

## Self-Review
- Spec §4.5 / three-surface voice → V2 worker + V3 browser client; voice SOS shares `sos_events` (V1 `/api/voice/sos` + V2 `raise_sos`) so the deferred dashboard will see it. Trilingual persona → V2. Testable-without-SwiftChat → V3 browser Call (the chosen approach).
- Can't offline-test the live call — V1 endpoints are pytest-covered; V2/V3 are import/build-verified; live call verified post-deploy with creds. Flagged, not hidden.
- Deferred (correct): SwiftChat native phone-icon dispatch (works once the ConveGenius bot registration exists — our `AGENT_NAME` + dispatch are compatible); transcript-summary enrichment (reference extra, out of scope).
- Consistency: `AGENT_NAME`, `/api/voice/token`, `/api/voice/sos`, `getVoiceToken`, `raise_sos`, job-metadata `{user_id,yatra,language}` used identically across worker, web, and client.
