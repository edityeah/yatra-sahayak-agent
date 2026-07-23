# Maharashtra Yatra Sahayak — POC Design Spec

**Date:** 2026-07-23
**Status:** Approved design, pending implementation plan
**Owner:** Aditya (ConveGenius / Vani Futura engagement)
**Platform:** ConveGenius SwiftChat

---

## 1. Context & Purpose

### 1.1 Where this comes from
This POC responds to a vendor proposal by **Vani Futura (OPC) Pvt Ltd** to the **Government of Maharashtra (Revenue & Forest Dept, Relief & Rehabilitation)** for a *"Comprehensive Digital Application for Yatris Visiting Pilgrimage Sites in Maharashtra."*

The proposal's stated mandate is **NDMA Letter No. 04/2020/AdminMatter/Comn&IT (110954), dated 20 January 2026**, which relays a direction of the **DGsP/IGsP Conference 2025** (via MHA DM Division letter dated 05 January 2025) that States/UTs build a comprehensive digital app for pilgrims.

> ⚠️ **Unverified source.** The NDMA/MHA letter is an internal government-to-government communication and is **not published anywhere publicly accessible**. We could not independently verify the letter number, date, or wording — we have only Vani Futura's paraphrase. The *technical premise* (benchmark apps, IMD/Sachet/112 infrastructure) is real and verifiable; the *originating mandate* is not. This does not block the POC but should be understood by anyone relying on the mandate.

### 1.2 The NDMA Para 2 feature set (what the app must cover)
1. Weather
2. Travel advisories
3. Logistical services (ponies, transport)
4. Helpline numbers
5. Emergency drills
6. Warning / guiding road signage

### 1.3 What this POC is for
**A demo to win the government deal.** Optimise for breadth of the six features looking real and convincing, in Marathi/Hindi/English, on believable Maharashtra yatras. Feasibility credibility matters (hence "as live as possible"), but a reliable on-stage story wins over fragile live wiring.

### 1.4 Decisions locked during brainstorming
| Decision | Choice |
|----------|--------|
| POC purpose | Demo to win the govt deal |
| Yatras | **Pandharpur Wari** + **Simhastha Kumbh (Nashik)**, with a switcher |
| Languages | **All three** — Marathi, Hindi, English |
| Data fidelity | **As live as possible** (with honest labelling — see §7) |
| Build pattern | Mirror `edityeah/swift-learning-agent` (Pravasi Setu) |
| Surfaces | **Full three-surface mirror** — chat + voice + embedded web apps |
| Web-app delivery | **BotExtension web-app "activities" only** — no standalone MiniApp |
| War-room | **Second chat agent** for officers, with a dashboard web-app activity |
| Registration | **Simulated** registration + simulated Aadhaar-style e-KYC (no real Aadhaar) |

---

## 2. Reference Architecture (the pattern we mirror)

`edityeah/swift-learning-agent` (Pravasi Setu Assistant) — one product, multiple surfaces, one backend:

- **agent/** — Python 3.11 · FastAPI · **LangGraph** state machine · OpenAI `gpt-4o-mini` · SSE streaming · psycopg-async → Supabase. Deployed on Render (web).
- **agent/voice_agent.py** — LiveKit Agents 1.6 + OpenAI Realtime (`gpt-realtime`), separate worker process, function-tools. Deployed on Render (worker).
- **webview/** — React 18 · Vite · React Router SPA on Vercel; SwiftChat SDKs loaded via CDN.
- **Supabase Postgres** — shared DB; nodes are stateless per request (state inferred from transcript + DB).
- LangGraph flow: `content_policy → course_selector (router, structured output) → {feature nodes} → END`.
- Rich UI blocks ride an **outbound POST** to SwiftChat; text deltas ride the **SSE stream**.

We keep this stack **identical**. Only the domain and surfaces change.

---

## 3. Target Architecture — Maharashtra Yatra Sahayak

```
   SwiftChat host
   ├── Bot A: "Maharashtra Yatra Sahayak"   (yatri chat agent)
   │      activities open web apps via BotExtension:
   │        /yatri/pass        — QR yatra pass
   │        /yatri/map         — live route map (halts, POIs, signage)
   │        /yatri/logistics   — notified-rate directory + providers
   │        /yatri/drills       — preparedness AV modules
   │        /yatri/advisories  — advisory feed
   │      + voice call (LiveKit + Realtime), SOS-capable
   │
   └── Bot B: "Yatra Control Room"          (officer chat agent — same pattern)
          activity opens web app via BotExtension:
            /control-room/dashboard — SOS queue · registrations · broadcast · analytics

   Both bots + both web surfaces
        → one FastAPI / LangGraph backend
        → shared Supabase Postgres
        → external: IMD weather (live) · tel: dial · Sachet/112 (own endpoint, see §7)
```

### 3.1 Surfaces
- **Two SwiftChat bots (chat agents):** a **yatri agent** (Bot A) and an **officer/war-room agent** (Bot B). Same build pattern for both (like Pravasi Setu's Assistant + Grievance Officer bots).
- **One SDK — `BotExtension` only.** Every web view (yatri and officer) is launched as an **activity from its own bot** and embedded via BotExtension. **No `MiniAppExtension`.**
- **Voice surface** on Bot A (LiveKit + OpenAI Realtime), same persona, SOS-capable.
- **"Connected":** each chat agent and its web app(s) share the backend/DB. An officer can chat *and* drive the dashboard; a yatri's SOS raised in chat/voice appears live in the officer's dashboard web app.

### 3.2 Repository layout (new repo, mirrors reference)
```
yatra-sahayak-agent/
├── agent/                      # FastAPI + LangGraph
│   ├── webhook.py              # HTTP endpoints (both bots share, routed by agent id)
│   ├── voice_agent.py          # LiveKit worker (SOS-capable)
│   └── agent/
│       ├── config.py · graph.py · state.py · streaming.py · db.py
│       ├── i18n.py             # Mr/Hi/En string + content resolution
│       ├── nodes/
│       │   ├── content_policy.py     # safety + SOS tripwire
│       │   ├── language_gate.py      # detect/persist language
│       │   ├── yatra_context.py      # which yatra (Wari/Kumbh) + switcher
│       │   ├── intent_router.py      # RouteDecision (structured output)
│       │   ├── weather.py · advisory.py · logistics.py
│       │   ├── helpline.py · drills_sos.py · signage.py
│       │   └── registration.py       # simulated e-KYC → QR pass
│       ├── officer/                  # war-room agent nodes (Bot B)
│       └── voice/                    # voice worker helpers + tools
├── webview/                    # React + Vite SPA (Vercel)
│   └── src/
│       ├── yatri/              # /yatri/* web apps
│       ├── control-room/       # /control-room/* dashboard
│       └── lib/swiftchat.js    # BotExtension wrapper
├── data/                       # seed content (rates, routes, signage, drills, advisories)
├── docs/
└── render.yaml
```

---

## 4. The Agent — LangGraph Flow

Both bots are LangGraph state machines. **Bot A (yatri):**

```
input
  → content_policy / SOS-tripwire   (safety gate; panic keywords fast-path to SOS)
  → language_gate                   (detect Mr/Hi/En; persist to user_state)
  → yatra_context                   (Pandharpur ⇄ Kumbh; the switcher)
  → intent_router                   (structured-output RouteDecision)
  → { weather | advisory | logistics | helpline | drills_sos | signage | registration | open_webapp | off_topic }
  → END
```

- **content_policy** — reused tripwire regex + LLM classifier. Adds a **panic/SOS keyword tripwire** that fast-paths to `drills_sos` in SOS mode.
- **language_gate** — detects Marathi/Hindi/English, responds in kind, persists preference in `user_state`.
- **yatra_context** — resolves which yatra the user is on; handles the explicit switch between Pandharpur Wari and Simhastha Kumbh.
- **intent_router** — deterministic `RouteDecision` (structured output), routes to one of the seven activities / `open_webapp` / `off_topic`.

**Bot B (officer)** is a smaller graph: `content_policy → officer_router → { sos_triage | broadcast | lookup | open_dashboard } → END`, gated by the `control_room_officers` allowlist.

---

## 5. The Six NDMA Activities (+ Registration)

| Node | Behaviour | Emits / opens | Fidelity (see §7) |
|------|-----------|---------------|-------------------|
| **weather** | Route/halt-wise forecast + rain/heat/lightning alert | weather card | **Live** (IMD) w/ cached fallback |
| **advisory** | District advisories, road closures, Palkhi schedule | advisory list + push | Admin-posted (DB) + feed where available |
| **logistics** | Govt-notified rates (transport/palkhi/porter/pony) + verified providers + overcharge report | opens `/yatri/logistics` | Canned real published rates |
| **helpline** | One-tap 112 / 108 / district control-room | quick-reply `tel:` buttons | **Real mechanism** (dials real number) |
| **drills_sos** | (a) preparedness AV modules; (b) **SOS** — capture GPS → `sos_events` → dashboard live; opt-in tracking | SOS confirm + map | AV canned; **SOS+GPS live** to our dashboard |
| **signage** | Geo-tagged signage layer + turn-by-turn voice | opens `/yatri/map` | Canned geo-data for 1–2 corridors |
| **registration** | **Simulated** e-KYC (name + phone, simulated Aadhaar KYC — no real Aadhaar) → **QR yatra pass**; group/Dindi reg; checkpoint headcount | opens `/yatri/pass` | Simulated e-KYC; real QR + scan logic |

### 5.1 QR Yatra Pass (detailed)
Modelled on Char Dham's *QR yatra pass* and Amarnath's *yatra permit*. It is **not** ticketing/payment — it is the thread tying a person to the safety system:

1. **Register once** — name, yatra (Wari/Kumbh), dates, group/Dindi, emergency contact, optional medical flags (elderly, heart condition). e-KYC step is **simulated** (a mocked Aadhaar-style KYC screen; no real Aadhaar captured or verified).
2. **System issues a unique Yatra ID + QR** encoding that ID; shown in the `/yatri/pass` web app.
3. **QR scanned at checkpoints** (Palkhi night-halts, ghat gates, darshan queues):
   - **Crowd analytics / headcount** → the emergency-drills / crowd-management half of the mandate (Kumbh stampede-prevention story).
   - **Identity-on-emergency** → scanning a found/unconscious yatri's pass pulls name + emergency contact + medical flags (missing-person protocol).

Chain: **registration → headcount → SOS identity → lost-and-found.**

---

## 6. Web Apps (BotExtension activities)

### 6.1 Yatri web apps (Bot A)
- `/yatri/pass` — QR yatra pass + registration flow (simulated e-KYC).
- `/yatri/map` — live route map: night-halts, medical posts, water points, toilets, signage points; turn-by-turn voice guidance.
- `/yatri/logistics` — notified-rate directory + verified providers + overcharge/grievance report.
- `/yatri/drills` — preparedness AV module library (stampede, ghat safety, first aid, heat, missing-person).
- `/yatri/advisories` — advisory feed (pushed from control room).
- Marathi-first; language switch to Hindi/English.

### 6.2 Control-room dashboard web app (Bot B)
- `/control-room/dashboard` — overview (registration counts, checkpoint flow) · **live SOS queue** (severity-sorted, location + tracking) · **alert broadcast** (compose → push to yatris) · lost-and-found · basic analytics (counts).
- **Auth:** `BotExtension.getPayload()` → `user_id`, checked server-side against a `control_room_officers` allowlist on every request. (Simpler than the reference's MiniApp SSO exchange.)

---

## 7. Integration Fidelity — Honest Labelling

So nobody oversells in the room, each feature is explicitly one of:

- **Truly live:** IMD weather · SOS + GPS → dashboard · one-tap `tel:` dial · voice-triggered SOS.
- **Real mechanism, our own backend** (real govt system needs an MoU we won't have for a POC):
  - **Sachet/CAP** alert broadcast — our own push, styled as CAP; not NDMA's live Sachet.
  - **ERSS-112 / 108** — dials the real number via `tel:`, but has **no CAD/dispatch integration**.
  - **e-KYC** — simulated Aadhaar-style KYC; no real Aadhaar captured or verified.
- **Canned but realistic:** notified logistics rates (real published numbers) · signage geo-data for 1–2 demo corridors · advisory seed · drill AV content.

> ⚠️ **Risk:** IMD's route-wise pilgrimage forecast may require key/registration we can't obtain in time. **Mitigation:** if live access fails, fall back to a **cached-but-real IMD snapshot** so the demo never dies on stage.

---

## 8. Trilingual (Marathi / Hindi / English)

- **Web-app UI:** i18n resource files (mr/hi/en).
- **Bot:** `language_gate` detects and responds in kind; LLM handles all three; preference persisted.
- **Seed content** (advisories, drill scripts, rate labels): authored/human-reviewed in all three for the demo path.
- **Voice:** OpenAI Realtime covers all three (Marathi quality to be validated; English fallback available).

---

## 9. Data Model (Supabase Postgres)

**Reference (seed) tables:** `yatras`, `routes`, `halts`, `poi` (medical/water/toilet), `logistics_rates`, `providers`, `signage_points`, `advisories`, `drills`.

**Transactional tables:** `yatris` (users), `registrations`, `yatra_passes`, `checkpoints`, `checkpoint_scans`, `sos_events`, `tracking_pings`, `alerts`, `control_room_officers`, `grievances` (overcharge reports).

Idempotent `CREATE TABLE IF NOT EXISTS` migrations on cold start (reference pattern).

---

## 10. Tech Stack (identical to reference)

- **Agent:** Python 3.11 · FastAPI · LangGraph · LangChain · OpenAI `gpt-4o-mini` (structured outputs) · psycopg 3 async · pydantic-settings · httpx.
- **Voice:** LiveKit Agents 1.6 · livekit-plugins-openai · OpenAI Realtime `gpt-realtime`.
- **Web:** React 18 · Vite · React Router v6 · native fetch · lucide-react · SwiftChat `BotExtension` SDK (CDN).
- **Infra:** Render (web + worker) · Vercel (webview) · Supabase Postgres · LiveKit Cloud (ConveGenius project) · OpenAI.

---

## 11. Demo Script (the winning narrative)

1. Open **Bot A in Marathi**. "I'm walking the Pandharpur Wari." → register → **QR yatra pass** (`/yatri/pass`).
2. "आजचं हवामान?" → **live IMD forecast** for the Wari route + rain alert.
3. Ask pony/transport rates → **logistics directory** with notified rates.
4. **Switch to Kumbh** — same agent, Nashik context.
5. Emergency: **voice call raises SOS** → **Bot B control-room dashboard lights up live** with location + pass identity.
6. Control room **broadcasts an advisory** → yatri receives it.
7. Show **signage map + turn-by-turn**.
8. Flip to **Hindi / English** to prove trilingual.

---

## 12. Scope Guardrails (YAGNI for the POC)

- No real Aadhaar/e-KYC, no real ERSS-112 CAD, no official Sachet broadcast — all simulated with real mechanisms.
- Two yatras only; 1–2 corridors each.
- Analytics = counts, not full BI.
- All demo data clearly labelled "POC".
- Voice: single happy-path SOS + weather + helpline tools; not full conversational parity with text.

---

## 13. Open Items / To Validate During Implementation

- IMD API access + a route-wise endpoint for Pandharpur & Nashik corridors (else cached snapshot).
- OpenAI Realtime Marathi voice quality.
- Two separate SwiftChat bot registrations (yatri + officer) + one Supabase + Render/Vercel deploys — confirm ConveGenius platform-side wiring.
- Exact notified-rate sources for Wari/Kumbh logistics (which govt notification to cite).
