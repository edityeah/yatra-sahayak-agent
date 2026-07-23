# Deploying Maharashtra Yatra Sahayak (POC)

Two pieces: the **agent** (FastAPI, Render) and the **webview** (React SPA, Vercel). They talk over HTTP; the webview needs the agent's public URL + the shared API key.

## Prerequisites (yours to provide)
- An **OpenAI API key** with access to `gpt-4o-mini` (the intent router + safety gate need it; without it, free-text classification fails open and only the deterministic paths — language/yatra selection, SOS, the web-app URLs — work).
- A **Render** account (agent) and a **Vercel** account (webview). I can't create accounts or enter your credentials — these steps are yours; each is one action.

## 1. Agent → Render
The repo already has `render.yaml` (a `web` service rooted at `agent/`).
1. In Render: **New → Blueprint**, point it at this repo. It picks up `render.yaml`.
2. Set env vars (dashboard, marked `sync: false`):
   - `OPENAI_API_KEY` = your key
   - `PUBLIC_WEBVIEW_BASE` = your Vercel URL once known (e.g. `https://yatra-sahayak.vercel.app`) — used for the activity/pass links the bot returns. You can set a placeholder first, then update after step 2.
   - `INTERNAL_API_KEY` is auto-generated (`generateValue: true`) — copy its value; the webview needs the same value.
   - Leave `DATABASE_URL` empty for in-memory (fine for a demo), or set a Supabase transaction-pooler URL for durable state.
3. Deploy. Health check: `https://<your-agent>.onrender.com/health` → `{"status":"ok",...}`.

## 2. Webview → Vercel
1. In Vercel: **New Project** from this repo; set **Root Directory = `webview/`**.
2. Env vars (Production + Preview):
   - `VITE_AGENT_URL` = `https://<your-agent>.onrender.com` (origin only — the app appends `/messages` and `/api/...`)
   - `VITE_AGENT_KEY` = the `INTERNAL_API_KEY` value from Render
3. Deploy. Vercel builds `webview/` (Vite) and serves the SPA (`vercel.json` handles the SPA fallback).
4. Go back to Render and set `PUBLIC_WEBVIEW_BASE` to the Vercel URL, so the bot's pass/map links point at the live site.

## 3. Test (no SwiftChat needed)
Open the Vercel URL. The **in-browser chat** exercises the whole bot; the web apps open at `/yatri/map`, `/yatri/logistics`, `/yatri/drills`, `/yatri/advisories`, and `/yatri/pass?id=<yatra_id>`. This is enough to demo without any SwiftChat registration.

## 4. SwiftChat registration (later, ConveGenius platform-side)
To run inside SwiftChat rather than a browser: register a bot whose webhook points at `https://<your-agent>.onrender.com/messages`, and register the web apps as BotExtension activities pointing at the Vercel routes. This is a ConveGenius platform step, out of scope for this repo. The browser flow above covers testing until then.

## 5. Voice (optional — Plan 5)
The browser **Call** button (`/voice`) + a LiveKit voice worker. It degrades gracefully: if LiveKit isn't configured, `/api/voice/token` returns 503 and the Call page shows "voice isn't enabled yet" — the rest of the app is unaffected. To enable it:

**Prerequisites:** a LiveKit Cloud project (ConveGenius's is fine) — `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`; an `OPENAI_API_KEY` with **Realtime (`gpt-realtime`) access**; and a Render **paid** plan for the worker (the free plan has no workers).

1. **Render — web service** (`yatra-sahayak-agent`): add `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (it mints join tokens + dispatches the worker). `AGENT_NAME` is already set to `yatra-sahayak-voice`.
2. **Render — worker service** (`yatra-sahayak-voice`, defined in `render.yaml`): set `OPENAI_API_KEY` (Realtime-enabled), `LIVEKIT_URL/API_KEY/API_SECRET`, `AGENT_API_HOST` = the web service URL (e.g. `https://yatra-sahayak-agent.onrender.com`), `AGENT_API_KEY` = the web service's `INTERNAL_API_KEY`. `AGENT_NAME` is preset. Deploy it (it registers under `AGENT_NAME` and waits for dispatches).
3. **Vercel — webview:** no new env needed (the Call button uses the existing `VITE_AGENT_URL`/`VITE_AGENT_KEY`).

**Live-test checklist:** open `<vercel-url>/voice` → tap **Call** → grant mic → you should hear Setu's greeting → say "there's a stampede, help" → Setu calls `raise_sos`, which creates a `sos_event` on the web service and tells you the control room is alerted + call 112. (The same store the text SOS uses — the future control-room dashboard will read both.)

> Voice runs inside SwiftChat too (the phone icon) once the ConveGenius bot registration wires our `AGENT_NAME` — no code change needed; the browser Call button is just the standalone test path.

## Run locally (what the maintainer does)
```bash
# agent
cd agent && python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
OPENAI_API_KEY=sk-... uvicorn webhook:app --port 8000

# webview (second terminal)
cd webview && npm install
cp .env.example .env    # defaults point at http://localhost:8000 / local-dev-key
npm run dev             # → http://localhost:5174
```
Then open http://localhost:5174.

> Note on live IMD weather: set `IMD_API_URL` on the agent to enable live forecasts; unset, the agent serves a realistic cached fallback (`data/weather_fallback.json`) so the demo never breaks.
