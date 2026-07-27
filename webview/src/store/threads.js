// Client-side thread + message store for the chat surfaces. There is no
// server-side conversation history for the webview (the agent is stateless per
// conversation_id), so past chats live in localStorage only — per-device.
// makeThreadStore(ns) creates an isolated store; the yatri agent uses the
// default instance (named exports), the officer agent gets its own namespace.

function safeParse(json, fallback) {
  try {
    const v = JSON.parse(json);
    return v && typeof v === "object" ? v : fallback;
  } catch (e) {
    return fallback;
  }
}
function uid(prefix = "t") {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function makeThreadStore(ns = "ysahayak") {
  const THREADS_KEY = `${ns}.threads.v1`;
  const ACTIVE_KEY = `${ns}.activeThread.v1`;
  const EVENT = `${ns}:threads:changed`;

  const fire = () => { try { window.dispatchEvent(new CustomEvent(EVENT)); } catch (e) { /* */ } };

  function loadThreads() {
    if (typeof window === "undefined") return {};
    return safeParse(window.localStorage.getItem(THREADS_KEY), {});
  }
  function saveThreads(threads) {
    try { window.localStorage.setItem(THREADS_KEY, JSON.stringify(threads)); } catch (e) { /* */ }
    fire();
  }
  function loadActiveId() {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACTIVE_KEY) || null;
  }
  function saveActiveId(id) {
    try { if (id) window.localStorage.setItem(ACTIVE_KEY, id); else window.localStorage.removeItem(ACTIVE_KEY); }
    catch (e) { /* */ }
    fire();
  }
  function createThread({ title = "New chat" } = {}) {
    const now = Date.now();
    const thread = { id: uid("t"), title, createdAt: now, updatedAt: now, messages: [] };
    const threads = loadThreads();
    threads[thread.id] = thread;
    saveThreads(threads);
    saveActiveId(thread.id);
    return thread;
  }
  function appendMessage(threadId, msg) {
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
  function deleteThread(id) {
    const threads = loadThreads();
    delete threads[id];
    saveThreads(threads);
    if (loadActiveId() === id) saveActiveId(null);
  }
  function subscribe(cb) {
    const onCustom = () => cb();
    window.addEventListener(EVENT, onCustom);
    window.addEventListener("storage", onCustom);
    return () => { window.removeEventListener(EVENT, onCustom); window.removeEventListener("storage", onCustom); };
  }
  return { loadThreads, loadActiveId, saveActiveId, createThread, appendMessage, deleteThread, subscribe };
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

// Default (yatri) instance — preserves the original named-export API.
const _default = makeThreadStore("ysahayak");
export const loadThreads = _default.loadThreads;
export const loadActiveId = _default.loadActiveId;
export const saveActiveId = _default.saveActiveId;
export const createThread = _default.createThread;
export const appendMessage = _default.appendMessage;
export const deleteThread = _default.deleteThread;
export const subscribe = _default.subscribe;
