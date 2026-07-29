import { getContext } from "./swiftchat";

const BASE = import.meta.env.VITE_AGENT_URL || "http://localhost:8000";
const KEY = import.meta.env.VITE_AGENT_KEY || "local-dev-key";

const _sleep = (ms) => new Promise((res) => setTimeout(res, ms));

// The agent runs on a free tier that sleeps when idle, so the first request
// after a lull can fail or 5xx while it cold-starts (~10–30s). Retry GETs a
// few times with backoff so a cold start recovers instead of surfacing as
// "no data". A 4xx (bad request/not found) is NOT retried — it won't change.
export async function apiGet(path, { retries = 3 } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(`${BASE}${path}`, { headers: { "X-API-Key": KEY } });
      if (r.ok) return r.json();
      if (r.status >= 400 && r.status < 500) throw new Error(`${path} -> ${r.status}`);
      lastErr = new Error(`${path} -> ${r.status}`);   // 5xx → retry
    } catch (e) {
      lastErr = e;   // network error (cold start / DNS) → retry
    }
    if (attempt < retries) await _sleep(1200 * (attempt + 1));   // 1.2s, 2.4s, 3.6s
  }
  throw lastErr;
}

export async function apiPost(path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": KEY },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

// Stream a chat turn from the agent's /messages SSE endpoint (POST). Calls
// onDelta(textChunk) as text arrives. Returns the full reply string.
export async function streamChat({ user_id, conversation_id, text, location, language, yatra }, onDelta) {
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
  const resp = await fetch(`${BASE}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": KEY },
    body: JSON.stringify({
      user_id, conversation_id, language, yatra,
      message: { content },
    }),
  });
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
