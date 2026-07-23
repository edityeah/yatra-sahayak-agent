// Client-side thread + message store for the Yatra chat surface. There is
// no server-side conversation history for the webview (the agent is
// stateless per conversation_id), so past chats live in localStorage only —
// per-device, per-browser. Mirrors the shape of the SwiftChat agentStore
// reference but is fully synchronous and localStorage-backed.

const THREADS_KEY = "ysahayak.threads.v1";
const ACTIVE_KEY = "ysahayak.activeThread.v1";
const EVENT = "ysahayak:threads:changed";

function safeParse(json, fallback) {
  try {
    const v = JSON.parse(json);
    return v && typeof v === "object" ? v : fallback;
  } catch (e) {
    return fallback;
  }
}

function fire() {
  try {
    window.dispatchEvent(new CustomEvent(EVENT));
  } catch (e) {
    /* ignore — non-browser environment */
  }
}

function uid(prefix = "t") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function loadThreads() {
  if (typeof window === "undefined") return {};
  return safeParse(window.localStorage.getItem(THREADS_KEY), {});
}

function saveThreads(threads) {
  try {
    window.localStorage.setItem(THREADS_KEY, JSON.stringify(threads));
  } catch (e) {
    /* ignore — quota / private mode */
  }
  fire();
}

export function loadActiveId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_KEY) || null;
}

export function saveActiveId(id) {
  try {
    if (id) window.localStorage.setItem(ACTIVE_KEY, id);
    else window.localStorage.removeItem(ACTIVE_KEY);
  } catch (e) {
    /* ignore */
  }
  fire();
}

export function createThread({ title = "New chat" } = {}) {
  const now = Date.now();
  const thread = { id: uid("t"), title, createdAt: now, updatedAt: now, messages: [] };
  const threads = loadThreads();
  threads[thread.id] = thread;
  saveThreads(threads);
  saveActiveId(thread.id);
  return thread;
}

export function appendMessage(threadId, msg) {
  const threads = loadThreads();
  const thread = threads[threadId];
  if (!thread) return null;
  const message = { ...msg };
  thread.messages = [...(thread.messages || []), message];
  thread.updatedAt = Date.now();
  if ((!thread.title || thread.title === "New chat") && msg.role === "user" && msg.text) {
    thread.title = String(msg.text).slice(0, 40);
  }
  threads[threadId] = thread;
  saveThreads(threads);
  return message;
}

export function deleteThread(id) {
  const threads = loadThreads();
  delete threads[id];
  saveThreads(threads);
  if (loadActiveId() === id) saveActiveId(null);
}

export function groupByRecency(list, now = Date.now()) {
  const sorted = [...list].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  const day = 24 * 60 * 60 * 1000;
  const groups = { today: [], yesterday: [], prev30: [], older: [] };
  for (const t of sorted) {
    const age = now - (t.updatedAt || 0);
    if (age < day) groups.today.push(t);
    else if (age < 2 * day) groups.yesterday.push(t);
    else if (age < 30 * day) groups.prev30.push(t);
    else groups.older.push(t);
  }
  return groups;
}

export function subscribe(cb) {
  const onCustom = () => cb();
  window.addEventListener(EVENT, onCustom);
  // Also react to storage events from other tabs of the same origin.
  window.addEventListener("storage", onCustom);
  return () => {
    window.removeEventListener(EVENT, onCustom);
    window.removeEventListener("storage", onCustom);
  };
}
