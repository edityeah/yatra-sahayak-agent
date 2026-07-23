# Yatra Sahayak — Plan 6: Pravasi-Setu-style UI redo (webview)

> Front-end plan; verification = `npm run build` passes + the controller drives it in a browser (Browser pane) and screenshots against the reference. Steps use `- [ ]`.

**Goal:** Replace the generic webview shell with a faithful replica of the **Pravasi Setu Assistant** UI (`edityeah/swift-learning-agent` webview + live `test-learning.adityeah.ai`): a chat landing with a Header (avatar + title), the big **yellow-ring "AI" avatar EmptyState**, a **QUICK ACTIVITIES** chip bar above the composer, a **QuickActivitiesSheet** drawer, and a `[+] input [mic]` **Composer** — adapted to Yatra content, trilingual, wired to our existing SSE chat + web-app routes.

**Architecture:** Adopt **Tailwind** with the reference's exact theme tokens (blue `primary #2563EB`, yellow `ai-ring #FACC15`, `ink/muted/surface` etc.) + `lucide-react` icons. Port the reference components (`Header`, `EmptyState`, `QuickActivities`, `QuickActivitiesSheet`, `Composer`, a menu drawer) into our `webview/`, swapping content for Yatra and keeping our contracts (`streamChat`, `apiGet`, `getContext`, `useLang`, the `/yatri/*` + `/voice` routes). The inner web-app pages (pass/map/logistics/drills/advisories/voice) stay functional and get re-skinned to the new palette.

**Reference (READ):** `…/scratchpad/swift-learning-agent/webview/` — `tailwind.config.js`, `src/index.css`, `src/agent/ChatShell.jsx`, `src/agent/components/{Header,EmptyState,QuickActivities,Composer}.jsx`, `src/agent/drawers/QuickActivitiesSheet.jsx`, and `src/store/chatClient.js` (`QUICK_ACTIVITIES` shape). The live look is the acceptance bar.

**Base:** branch `feat/plan-06-ui` off `feat/plan-05-voice` (has the latest webview incl. the `/voice` Call page).

---

## Yatra Quick Activities (the emphasized piece)
An array (in a `quickActivities.js`), each `{id, icon(emoji), label:{mr,hi,en}, tagline:{mr,hi,en}, action}` where `action` is either `{type:"send", text}` (send an intent to the chat so the bot responds) or `{type:"route", href}` (open a web app). Proposed set:
- 🪪 **Register / Yatra Pass** → send "I want to register for the yatra"
- 🌦️ **Weather** → send "what is the weather on the route today?"
- 🐎 **Transport & Rates** → send "what are the transport and pony rates?"
- ☎️ **Helplines** → send "give me the emergency helpline numbers"
- 🧭 **Route Map** → route `/yatri/map`
- 📢 **Advisories** → route `/yatri/advisories`
- 🆘 **Safety & Drills** → send "what safety drills should I know?"
- 📞 **Call (voice)** → route `/voice`
Bar shows the first 3–4 as chips + "See all"; the sheet lists all. Tapping a `send` chip pushes the text as a user turn; a `route` chip navigates.

---

## Task U1: Tailwind + theme + lucide (foundation)
**Files:** `webview/package.json` (+`tailwindcss`,`postcss`,`autoprefixer`,`lucide-react`), `webview/tailwind.config.js`, `webview/postcss.config.js`, `webview/src/index.css` (or `styles.css`) with `@tailwind` + the reference animations, `webview/src/main.jsx` (import the css).
- Port `tailwind.config.js` theme (colors/shadows/fontFamily) verbatim from the reference. Add the `animate-slide-in-right/left`, `animate-fade-in` utilities + keyframes (from ref `index.css`).
- Keep the app building (`npm run build`) with Tailwind active; existing plain-CSS pages keep working during transition (leave `styles.css` in place; Tailwind is additive).
- Commit `feat(webview): add Tailwind + Pravasi-Setu theme tokens + lucide`.

## Task U2: Chat shell — Header, EmptyState, Composer, menu (Pravasi Setu look)
**Files:** `webview/src/chat/ChatPage.jsx` (rewrite), `webview/src/components/chat/{Header,EmptyState,Composer,MenuDrawer}.jsx`.
- **Header**: h-14, back arrow, round `primary-100` avatar with a pilgrimage icon (`lucide-react` `Landmark` or `Tent`), bold title "Maharashtra Yatra Sahayak" + the active yatra as a subtitle, right-side menu (hamburger) opening `MenuDrawer` (which holds the **language switch mr/hi/en** + links + "New chat"). Mirror ref `Header.jsx`.
- **EmptyState**: the yellow-ring avatar (`ai-ring`/`ai-ring-soft`, 128px), white inner circle + pilgrimage icon, blue "✨ AI" pill top-right, trilingual tagline (e.g. mr "तुमच्या यात्रेला मार्गदर्शन — पावलोपावली"). Mirror ref `EmptyState.jsx`.
- **Composer**: `[+]` primary round button (opens the QuickActivitiesSheet or menu), rounded `surface-2` input (trilingual placeholder), Send when text / a Mic button that routes to `/voice` (our voice Call) when empty. Mirror ref `Composer.jsx`.
- **ChatPage** keeps the existing `streamChat` flow + stable conversation_id + markdown rendering; shows EmptyState when no messages, MessageList when there are. Keep the `warmUpAgent` health ping (wake Render free tier). Language from `useLang()`.
- Commit `feat(webview): Pravasi-Setu chat shell (header, AI empty state, composer)`.

## Task U3: QuickActivities bar + Sheet (the centerpiece)
**Files:** `webview/src/data/quickActivities.js`, `webview/src/components/chat/{QuickActivities,QuickActivitiesSheet}.jsx`, wire into `ChatPage`.
- `quickActivities.js`: the array above (trilingual label/tagline, `action`).
- **QuickActivities** bar: shown above the composer on the empty state — "✨ QUICK ACTIVITIES" label + up to 4 white pill chips (icon + label in current lang) + "See all". Mirror ref `QuickActivities.jsx`.
- **QuickActivitiesSheet**: right drawer listing all as icon-tile cards (label + tagline). Mirror ref `QuickActivitiesSheet.jsx`.
- Tapping: `action.type==="send"` → push the text as a chat turn (calls ChatPage's send); `action.type==="route"` → `navigate(href)`. Close the sheet on pick.
- Commit `feat(webview): Yatra Quick Activities bar + sheet`.

## Task U4: Re-skin inner pages + verify + screenshots
**Files:** the `/yatri/*` + `/voice` pages (Pass/Map/Logistics/Drills/Advisories/Call) — swap the old AppShell/ui for the new header + Tailwind tokens so they feel part of one app; keep all data/logic. Remove the now-unused old `AppShell.jsx`/`ui.jsx` if fully replaced (or keep if still referenced).
- `npm run build` passes.
- Controller runs agent + webview locally, drives in the Browser pane: chat landing matches the reference (header, AI avatar, quick-activities bar); open the sheet; tap a "send" chip (bot responds) + a "route" chip (opens map); check a couple inner pages re-skinned. Screenshot the landing next to the reference.
- Commit `feat(webview): re-skin yatri pages to the new shell; verify UI parity`.

---

## Self-Review
- Matches the reference's Header / EmptyState / QuickActivities(bar+sheet) / Composer structure + exact theme tokens; content is Yatra + trilingual; the emphasized "quick activities" appear both as the chip bar and the full sheet, mapping to chat-sends and web-app routes.
- Keeps every existing contract (streamChat, apiGet, getContext, useLang, routes) so no backend change and no lost functionality (chat, pass, map, lists, voice).
- Verified by build + live browser parity check (front-end), not unit tests.
- Deferred: pixel-perfect thread history/drawer (we have no DB threads — MenuDrawer is lighter than the reference's ThreadsDrawer); that's an acceptable POC simplification.
