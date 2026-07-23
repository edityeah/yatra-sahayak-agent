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
