import { getContext } from "./swiftchat";

const BASE = import.meta.env.VITE_AGENT_URL || "http://localhost:8000";
const KEY = import.meta.env.VITE_AGENT_KEY || "local-dev-key";

const _sleep = (ms) => new Promise((res) => setTimeout(res, ms));

// The agent runs on a free tier that SLEEPS when idle; the first request after
// a lull can take 30–60s to cold-start (edge returns a network error or
// 502/503/504 until the app boots). We retry across a window LONGER than a full
// cold start so activities always recover instead of showing "couldn't load".
// `onWaking(n)` fires after the first miss so the page can show a "waking up"
// state instead of a scary error. A 4xx (or app-level 500) is the server's real
// answer and is NOT retried — it won't change.
const _GATEWAY = new Set([502, 503, 504]);           // proxy-level = never reached the app
// Backoff capped at 5s; total window ≈ 1+2+3+4+5 + 5·(retries-4) seconds.
const _backoff = (attempt) => Math.min(1000 * (attempt + 1), 5000);

export async function apiGet(path, { retries = 14, onWaking } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(`${BASE}${path}`, { headers: { "X-API-Key": KEY } });
      if (r.ok) return r.json();
      if (r.status >= 400 && r.status < 500) throw new Error(`${path} -> ${r.status}`);
      lastErr = new Error(`${path} -> ${r.status}`);   // 5xx / cold start → retry
    } catch (e) {
      lastErr = e;   // network error (cold start / DNS) → retry
    }
    if (attempt < retries) { onWaking?.(attempt + 1); await _sleep(_backoff(attempt)); }
  }
  throw lastErr;
}

export async function apiPost(path, body, { retries = 10, onWaking } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(`${BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": KEY },
        body: JSON.stringify(body || {}),
      });
      if (r.ok) return r.json();
      // Only proxy-level failures are safe to retry (the request never reached
      // the app, so no double-submit). A 4xx/500 is the app's real answer.
      if (!_GATEWAY.has(r.status)) throw new Error(`${path} -> ${r.status}`);
      lastErr = new Error(`${path} -> ${r.status}`);
    } catch (e) {
      lastErr = e;   // pre-response network error → never reached the app → retry
    }
    if (attempt < retries) { onWaking?.(attempt + 1); await _sleep(_backoff(attempt)); }
  }
  throw lastErr;
}

// Stream a chat turn from the agent's /messages SSE endpoint (POST). Calls
// onDelta(textChunk) as text arrives. Returns the full reply string.
export async function streamChat({ user_id, conversation_id, text, location, language, yatra }, onDelta, onWaking) {
  // Pass the known language so the agent replies in it. The YATRA is
  // deliberately NOT defaulted — it's selected in the chat itself, so when the
  // user hasn't picked one yet we send nothing and the agent asks.
  const ctx = getContext();
  language = language || ctx.language;
  // A shared location is sent as a native "location" content block — the same
  // shape SwiftChat's own location message uses — so the agent handles it
  // identically whether it came from SwiftChat's attachment or our composer.
  const content = location
    ? [{ type: "location", location: { latitude: location.lat, longitude: location.lng } }]
    : [{ type: "text", text: { value: text } }];
  const payload = JSON.stringify({ user_id, conversation_id, language, yatra, message: { content } });

  // Connect with cold-start resilience: the agent may be waking (30–60s), where
  // the edge returns a network error or 502/503/504 BEFORE the app streams. We
  // retry the CONNECTION (never mid-stream) so the chat never silently shows an
  // empty bubble. onWaking fires after the first miss so the UI can show it.
  let resp, lastErr;
  for (let attempt = 0; attempt <= 10; attempt++) {
    try {
      resp = await fetch(`${BASE}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": KEY },
        body: payload,
      });
      if (resp.ok && resp.body) break;
      if (!_GATEWAY.has(resp.status)) throw new Error(`/messages -> ${resp.status}`);
      lastErr = new Error(`/messages -> ${resp.status}`);   // gateway → cold start → retry
    } catch (e) {
      lastErr = e; resp = null;   // pre-response network error → retry
    }
    if (attempt < 10) { onWaking?.(attempt + 1); await _sleep(_backoff(attempt)); }
  }
  if (!resp || !resp.ok || !resp.body) throw lastErr || new Error("/messages failed");

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "", full = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // Frames are blank-line separated; the server (sse-starlette) emits
    // "\r\n\r\n", not "\n\n", so match either line-ending style.
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() || "";
    for (const frame of frames) {
      const lines = frame.split("\n");
      const ev = lines.find((l) => l.startsWith("event:"))?.slice(6).trim();
      const dataLine = lines.find((l) => l.startsWith("data:"))?.slice(5).trim();
      if (ev === "delta" && dataLine) {
        try {
          const d = JSON.parse(dataLine);
          if (d.o === "append" && typeof d.v === "string") { full += d.v; onDelta?.(d.v); }
        } catch (e) { /* ignore keepalive/non-json */ }
      }
    }
  }
  return full;
}

// Fetch a LiveKit room token for the browser voice call. Returns 503 (thrown
// as an Error with .code = 503) when voice isn't configured on this
// deployment — callers should show a friendly "unavailable" state, not crash.
export async function getVoiceToken({ user_id, yatra, language }) {
  const r = await fetch(`${BASE}/api/voice/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": KEY },
    body: JSON.stringify({ user_id, yatra, language }),
  });
  if (r.status === 503) { const e = new Error("voice-not-configured"); e.code = 503; throw e; }
  if (!r.ok) throw new Error(`voice token -> ${r.status}`);
  return r.json(); // { url, token, room }
}
