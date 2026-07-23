# Yatra Sahayak — Plan 3: Yatri Web Apps (+ browser chat & local hosting)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or executing-plans. Front-end tasks are verified by a passing `npm run build` + the controller driving the app in a browser (Browser pane) + screenshots, not by unit tests alone. Steps use `- [ ]`.

**Goal:** A React + Vite SPA (the yatri web surface) served as SwiftChat **BotExtension activities**, plus a simple in-browser **chat UI** so the whole bot can be exercised in a browser without a SwiftChat registration. Five activities open as web apps: **QR yatra pass**, **route map** (Leaflet + OpenStreetMap), **logistics directory**, **drills library**, **advisories feed**. The agent gains read-only JSON endpoints the SPA fetches. Everything runs locally for verification and is deploy-ready (Render for the agent, Vercel for the SPA).

**Architecture:** The Plan 1–2 agent is unchanged except for new **read-only `/api/*` endpoints** (seed + registration data). A new `webview/` React SPA (Vite, React Router, Leaflet) reads those endpoints. It loads SwiftChat's `BotExtension` SDK when embedded, with a **dev fallback** (URL `?user_id=` / a default) so it also runs as a plain website for testing. The chat UI streams from the agent's existing `/messages` SSE endpoint.

**Tech Stack:** React 18 · Vite 5 · React Router v6 · Leaflet 1.9 + react-leaflet · `qrcode` (client QR render) · native fetch/EventSource. Agent side: FastAPI (existing) + a few GET routes.

**Base:** branch `feat/plan-03-webapps` off Plan 2. Reference webview to mirror for conventions: `…/scratchpad/swift-learning-agent/webview/` (`index.html` loads the BotExtension SDK; `src/lib/swiftchat.js`; `src/agent/ChatShell.jsx`; `vercel.json`). Spec §6.1 (yatri web apps), §7 (trilingual). Node 24 / npm 11 available.

---

## File Structure

```
agent/webhook.py                      # MODIFY — add read-only /api/* GET routes
tests/test_api_endpoints.py           # NEW — endpoint tests (offline, in-memory)

webview/                               # NEW — Vite React SPA (Vercel-deployed)
├── index.html                        # loads BotExtension SDK (CDN) + mounts app
├── package.json · vite.config.js · vercel.json
├── .env.example                      # VITE_AGENT_URL, VITE_AGENT_KEY
├── public/                           # leaflet marker assets if needed
└── src/
    ├── main.jsx · App.jsx            # routes: / (chat), /yatri/{pass,map,logistics,drills,advisories}
    ├── lib/
    │   ├── swiftchat.js              # BotExtension wrapper + dev fallback (user_id, language, yatra)
    │   └── api.js                    # fetch helpers (X-API-Key) + SSE chat client
    ├── components/
    │   ├── AppShell.jsx              # header (yatra + language switch), nav, i18n strings
    │   └── ui.jsx                    # small shared UI (Card, Pill, Loading)
    ├── chat/ChatPage.jsx             # in-browser chat (streams /messages)
    └── yatri/
        ├── PassPage.jsx             # /yatri/pass?id= — registration + QR
        ├── MapPage.jsx             # /yatri/map?yatra= — Leaflet + POI pins
        ├── LogisticsPage.jsx      # /yatri/logistics?yatra=
        ├── DrillsPage.jsx         # /yatri/drills
        └── AdvisoriesPage.jsx     # /yatri/advisories?yatra=

.claude/launch.json                   # MODIFY — add a "webview" dev-server config
```

**i18n:** the SPA carries an `mr/hi/en` string table (a small `strings.js`), and resolves seed content's trilingual dicts the same way `seed.t` does on the server. Language comes from `?lang=` / BotExtension payload / a header switcher, defaulting to `mr`.

---

## Task 1: Agent read-only `/api/*` endpoints

**Files:** Modify `agent/webhook.py`; Create `tests/test_api_endpoints.py`.

Add GET routes (all require `X-API-Key: settings.INTERNAL_API_KEY`, which the SPA sends via `VITE_AGENT_KEY` — POC-grade; documented). Each returns JSON from `seed`/`persistence`:
- `GET /api/yatra/{yatra}/routes` → `seed.load("routes")[yatra]`
- `GET /api/yatra/{yatra}/logistics` → `seed.load("logistics_rates")[yatra]`
- `GET /api/yatra/{yatra}/advisories` → `seed.load("advisories")[yatra]`
- `GET /api/drills` → `seed.load("drills")`
- `GET /api/yatra/{yatra}` → `seed.load("yatras")[yatra]` (name, control_room)
- `GET /api/pass/{yatra_id}` → the registration row via `persistence.get_registration_by_id(yatra_id)` (ADD this helper to persistence: look up by PK in `_REGISTRATIONS`/DB). Returns 404 if missing. (PII exposed by opaque id — acceptable for POC; a real deploy scopes it to the authenticated yatri.)

A small `_require_key(x_api_key)` helper raises 401 on mismatch. Unknown yatra → 404. Invalid yatra names must not KeyError (guard with `.get`).

- [ ] **Step 1:** Add `persistence.get_registration_by_id(yatra_id)` (async; memory + DB branches, mirror `get_registration_for_user`). Test in `test_persistence.py` (append one case).
- [ ] **Step 2:** Write `tests/test_api_endpoints.py` (TestClient): 401 without key; `/api/yatra/pandharpur/logistics` returns a non-empty list with `service`; `/api/drills` returns a list; `/api/pass/{unknown}` → 404; after creating a registration via persistence, `/api/pass/{id}` returns the row.
- [ ] **Step 3:** Implement the routes in `webhook.py` (reuse `settings`; guard unknown yatra → 404).
- [ ] **Step 4:** `pytest -q` green.
- [ ] **Step 5:** Commit `feat(agent): read-only /api endpoints for the yatri web apps`.

## Task 2: Webview scaffold + SwiftChat/dev bridge + API client

**Files:** `webview/{index.html,package.json,vite.config.js,vercel.json,.env.example}`, `webview/src/{main.jsx,App.jsx}`, `webview/src/lib/{swiftchat.js,api.js}`, `webview/src/components/{AppShell.jsx,ui.jsx}`, `webview/src/strings.js`.

- Vite React SPA. `index.html` loads the BotExtension SDK from `cdn.convegenius.ai/public/bot_extension/sdk-v4.js` and bridges it to `window.BotExtension` (mirror the reference's `index.html`).
- `lib/swiftchat.js`: `getContext()` → `{user_id, language, yatra}` from `BotExtension.getPayload()` when present, else from URL query (`?user_id=&lang=&yatra=`), else defaults (`user_id="web-tester"`, `lang="mr"`, `yatra="pandharpur"`). This dev fallback is what lets the SPA run as a plain website.
- `lib/api.js`: `apiGet(path)` (adds `X-API-Key` from `import.meta.env.VITE_AGENT_KEY`, base `VITE_AGENT_URL` origin), and `streamChat(messages, onDelta)` hitting `${VITE_AGENT_URL}` (the `/messages` SSE) — parse the `event: delta` frames and append text.
- `App.jsx` routes: `/` → ChatPage; `/yatri/pass|map|logistics|drills|advisories`.
- `AppShell`: header with the yatra name + a language switcher (mr/hi/en) that updates a context; `strings.js` holds UI labels per language.
- `vercel.json`: SPA rewrite all → `/index.html`.
- [ ] `npm install` then `npm run build` must pass. Commit `feat(webview): scaffold SPA + SwiftChat/dev bridge + API client`.

## Task 3: In-browser Chat UI

**Files:** `webview/src/chat/ChatPage.jsx`.
A minimal chat: message list + composer; on send, POST to `/messages` (SSE) via `api.streamChat`, render streamed reply; keeps `conversation_id` stable per session; passes `user_id` from `swiftchat.getContext()`. Markdown rendering (links clickable — the activity links like `/yatri/map?yatra=` open the web apps; `tel:` links dial). This is the primary test surface. Commit `feat(webview): in-browser chat UI over /messages`.

## Task 4: QR Yatra Pass page

**Files:** `webview/src/yatri/PassPage.jsx`.
Reads `?id=<yatra_id>`, `apiGet('/api/pass/'+id)`; renders a pass card (name, yatra, group, Yatra ID) and a **QR code** (client-side `qrcode` lib encoding the Yatra ID) + a note that scanning it at checkpoints does headcount/identity. Loading + not-found states. Commit `feat(webview): QR yatra pass page`.

## Task 5: Route Map (Leaflet + OSM)

**Files:** `webview/src/yatri/MapPage.jsx`.
Reads `?yatra=`, `apiGet('/api/yatra/'+yatra+'/routes')`; renders a Leaflet map (OpenStreetMap tiles) centered on the yatra region, with markers for each route entry (night_halt/ghat/medical/water/toilet — distinct icons/colors), popups showing the trilingual name. Seed `routes` entries need coordinates — **ADD `lat`/`lng` to each `data/routes.json` entry** (plausible real coords: Pandharpur Palkhi towns Saswad/Jejuri/Wakhari/Lonand/Pandharpur; Nashik ghats Ramkund/Kushavarta/Panchavati). Fit bounds to markers. Commit `feat(webview): Leaflet route map + geo-tagged POIs` (+ `feat(data): add lat/lng to routes`).

## Task 6: Logistics, Drills, Advisories pages

**Files:** `webview/src/yatri/{LogisticsPage,DrillsPage,AdvisoriesPage}.jsx`.
Each fetches its `/api/*` endpoint and renders a clean, trilingual list (reuse `ui.jsx` Card): logistics = rate table + overcharge-report note; drills = expandable module cards; advisories = severity-badged feed. Commit `feat(webview): logistics, drills, advisories pages`.

## Task 7: Local run + verify + deploy prep

**Files:** Modify `.claude/launch.json`; `webview/README.md`; update root `README.md`.
- Add a `webview` launch config (`npm run dev`, its port).
- Controller runs agent (`uvicorn`, port 8000, with a real or placeholder key) + webview (`npm run dev`), opens the Browser pane, drives: chat greeting→language→yatra→ask weather/logistics/register; opens `/yatri/map?yatra=pandharpur` (map renders with pins), `/yatri/pass?id=<a registered id>` (QR renders), logistics/drills/advisories. Screenshot each. Fix issues found.
- Deploy prep: `webview/vercel.json` + `.env.example` documented; a `docs/DEPLOY.md` with the exact steps (Render: existing `render.yaml`, set `OPENAI_API_KEY`; Vercel: root `webview/`, set `VITE_AGENT_URL`=Render `/messages`, `VITE_AGENT_KEY`=INTERNAL_API_KEY). Note the SwiftChat bot registration is a separate ConveGenius step (out of scope; the browser chat covers testing without it).
- Commit `feat: local run config + deploy docs; verify yatri web apps end-to-end`.

---

## Self-Review
- Spec §6.1 five web apps → Tasks 4–6; browser chat (test surface) → Task 3; BotExtension + dev fallback → Task 2; trilingual → strings.js + seed.t-parity; live map → Task 5. Agent stays the source of truth via `/api/*` (Task 1).
- Deferred (correct): officer war-room dashboard + SwiftChat bot registration → later/Plan 4; voice → Plan 5.
- Front-end verification is build-pass + controller browser-driving + screenshots (no heavy unit tests); the agent `/api` endpoints get real pytest coverage (Task 1).
- Consistency: `/api/*` paths, `swiftchat.getContext()`, `api.apiGet/streamChat`, and the `?yatra=`/`?id=`/`?lang=` query contract are used identically across pages.
