import { getContext } from "./swiftchat";

const BASE = import.meta.env.VITE_AGENT_URL || "http://localhost:8000";
const KEY = import.meta.env.VITE_AGENT_KEY || "local-dev-key";

export async function apiGet(path) {
  const r = await fetch(`${BASE}${path}`, { headers: { "X-API-Key": KEY } });
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

// Stream a chat turn from the agent's /messages SSE endpoint (POST). Calls
// onDelta(textChunk) as text arrives. Returns the full reply string.
export async function streamChat({ user_id, conversation_id, text }, onDelta) {
  // The web app already knows the user's language (switcher / ?lang=) and the
  // active yatra (header). Pass them so the agent skips the in-chat language +
  // yatra prompts and goes straight to the intent (e.g. a "Register" tap).
  const { language, yatra } = getContext();
  const resp = await fetch(`${BASE}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": KEY },
    body: JSON.stringify({
      user_id, conversation_id, language, yatra,
      message: { content: [{ type: "text", text: { value: text } }] },
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
