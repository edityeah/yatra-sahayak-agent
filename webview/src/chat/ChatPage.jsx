import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Landmark } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { ErrorNote } from "../components/ui.jsx";
import { streamChat } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";
import Header from "../components/chat/Header.jsx";
import EmptyState from "../components/chat/EmptyState.jsx";
import QuickActivities from "../components/chat/QuickActivities.jsx";
import Composer from "../components/chat/Composer.jsx";
import PersistentMenuDrawer from "../components/chat/PersistentMenuDrawer.jsx";
import ThreadsDrawer from "../components/chat/ThreadsDrawer.jsx";
import { QUICK_ACTIVITIES } from "../data/quickActivities.js";
import { YATRA_NAMES } from "../data/yatraNames.js";
import {
  loadThreads,
  loadActiveId,
  saveActiveId,
  createThread,
  appendMessage,
  subscribe,
} from "../store/threads.js";

const TYPING = { mr: "टाइप करत आहे…", hi: "टाइप कर रहा है…", en: "typing…" };

// Very small markdown-ish renderer: **bold**, [label](url), bare URLs,
// tel: links, and line breaks. Returns an array of React nodes.
function renderMarkdown(text) {
  if (!text) return null;
  const lines = String(text).split("\n");
  const nodes = [];
  lines.forEach((line, li) => {
    if (li > 0) nodes.push(<br key={`br-${li}`} />);
    nodes.push(...renderInline(line, `l${li}`));
  });
  return nodes;
}

function renderInline(line, keyPrefix) {
  const re = /(\[([^\]]+)\]\((tel:[^)]+|https?:\/\/[^)]+)\))|(\*\*([^*]+)\*\*)|(tel:[+\d][\d-]*)|(https?:\/\/[^\s)]+)/g;
  const out = [];
  let last = 0;
  let m;
  let idx = 0;
  while ((m = re.exec(line))) {
    if (m.index > last) out.push(line.slice(last, m.index));
    if (m[1]) {
      out.push(
        <a key={`${keyPrefix}-${idx++}`} href={m[3]} className="text-primary font-bold underline decoration-2 underline-offset-2 hover:no-underline">
          {m[2]}
        </a>
      );
    } else if (m[4]) {
      out.push(<strong key={`${keyPrefix}-${idx++}`} className="font-extrabold">{m[5]}</strong>);
    } else if (m[6]) {
      out.push(
        <a key={`${keyPrefix}-${idx++}`} href={m[6]} className="text-primary font-bold underline decoration-2 underline-offset-2 hover:no-underline">
          {m[6]}
        </a>
      );
    } else if (m[7]) {
      out.push(
        <a key={`${keyPrefix}-${idx++}`} href={m[7]} className="text-primary font-bold underline decoration-2 underline-offset-2 hover:no-underline">
          {m[7]}
        </a>
      );
    }
    last = re.lastIndex;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}

function MessageBubble({ m, waitingFirstDelta, language }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-user text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-card">
          <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{m.text}</p>
        </div>
      </div>
    );
  }
  const isTyping = m.text === "" && waitingFirstDelta;
  return (
    <div className="flex gap-2.5">
      <div className="w-8 h-8 rounded-full bg-primary-100 text-primary flex items-center justify-center flex-shrink-0 mt-0.5">
        <Landmark size={16} />
      </div>
      <div className="flex-1 min-w-0 max-w-[80%]">
        <div className="bg-white text-ink rounded-2xl rounded-tl-md px-4 py-3 shadow-card border border-bdr-soft">
          {isTyping ? (
            <span className="text-[13px] text-muted italic">{t(TYPING, language)}</span>
          ) : (
            <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{renderMarkdown(m.text)}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// Best-effort wake-up ping for the agent's free-tier host — never blocks
// the UI and swallows any failure.
async function warmUpAgent() {
  try {
    const base = import.meta.env.VITE_AGENT_URL || "http://localhost:8000";
    await fetch(`${base}/health`);
  } catch (e) {
    /* ignore — best-effort only */
  }
}

// Detect the language the user is TYPING in, so the whole UI follows it.
// Latin script → English; Devanagari → keep the current mr/hi (can't be told
// apart from script), else Marathi; ambiguous (digits/punctuation) → no change.
function detectTypedLang(text, current) {
  const hasLatin = /[A-Za-z]/.test(text);
  const hasDev = /[ऀ-ॿ]/.test(text);
  if (hasLatin && !hasDev) return "en";
  if (hasDev && !hasLatin) return current === "hi" ? "hi" : "mr";
  return null; // no clear signal
}

export default function ChatPage() {
  const { language, setLanguage, yatra, setYatra } = useLang();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const ctx = useRef(getContext()).current;

  const [threads, setThreads] = useState(() => loadThreads());
  const [activeId, setActiveId] = useState(() => loadActiveId());

  const [busy, setBusy] = useState(false);
  const [waitingFirstDelta, setWaitingFirstDelta] = useState(false);
  const [streamText, setStreamText] = useState(null); // null = not streaming
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [threadsOpen, setThreadsOpen] = useState(false);
  const scrollRef = useRef(null);
  const seededRef = useRef(false);

  useEffect(() => {
    warmUpAgent();
  }, []);

  // Keep local state in sync with the localStorage-backed thread store
  // (covers updates made from the ThreadsDrawer — delete, pick, etc.).
  useEffect(() => {
    return subscribe(() => {
      setThreads(loadThreads());
      setActiveId(loadActiveId());
    });
  }, []);

  const activeThread = activeId ? threads[activeId] : null;
  const messages = activeThread?.messages || [];

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamText]);

  const send = useCallback(
    async (text) => {
      const clean = String(text || "").trim();
      if (!clean || busy) return;
      setError(null);

      // Sync the whole UI to the language the user is typing in.
      const typed = detectTypedLang(clean, language);
      if (typed && typed !== language) setLanguage(typed);

      let id = activeId;
      if (!id) {
        const th = createThread({});
        id = th.id;
        setActiveId(id);
      }

      appendMessage(id, { role: "user", text: clean });
      setThreads(loadThreads());

      setBusy(true);
      setWaitingFirstDelta(true);
      setStreamText("");

      try {
        const full = await streamChat(
          { user_id: ctx.user_id, conversation_id: id, text: clean, language, yatra },
          (chunk) => {
            setWaitingFirstDelta(false);
            setStreamText((prev) => (prev || "") + chunk);
          }
        );
        appendMessage(id, { role: "bot", text: full });
        setThreads(loadThreads());
      } catch (e) {
        setError(e?.message || String(e));
      } finally {
        setBusy(false);
        setWaitingFirstDelta(false);
        setStreamText(null);
      }
    },
    [activeId, busy, ctx.user_id, language, setLanguage]
  );

  // Consume a ?q=<text> deep link (handoff from the full-page Quick
  // Activities view) once, then strip it from the URL.
  useEffect(() => {
    if (seededRef.current) return;
    const q = searchParams.get("q");
    if (!q) return;
    seededRef.current = true;
    const next = new URLSearchParams(searchParams);
    next.delete("q");
    setSearchParams(next, { replace: true });
    send(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function handleQuickActivity(a) {
    if (a.action?.type === "route") {
      navigate(a.action.href);
      return;
    }
    send(a.action?.text || t(a.label, language));
  }

  function handlePickThread(id) {
    saveActiveId(id);
    setActiveId(id);
    setError(null);
    setThreadsOpen(false);
  }

  function handleNewChat() {
    const th = createThread({});
    setThreads(loadThreads());
    setActiveId(th.id);
    setError(null);
    setThreadsOpen(false);
  }

  const isEmpty = messages.length === 0 && streamText === null;

  return (
    <div className="h-screen flex flex-col overflow-hidden font-sans bg-surface text-ink">
      <Header
        yatra={yatra}
        onYatraChange={setYatra}
        onMenu={() => setThreadsOpen(true)}
        onCall={() => navigate("/voice")}
      />

      <div className="flex-1 min-h-0 overflow-y-auto" ref={scrollRef}>
        <div className="max-w-3xl w-full mx-auto px-4 sm:px-6 pt-4 pb-4">
          {isEmpty ? (
            <EmptyState />
          ) : (
            <div className="pt-2 space-y-3">
              {messages.map((m, i) => (
                <MessageBubble key={i} m={m} waitingFirstDelta={false} language={language} />
              ))}
              {streamText !== null && (
                <MessageBubble
                  key="streaming"
                  m={{ role: "bot", text: streamText }}
                  waitingFirstDelta={waitingFirstDelta}
                  language={language}
                />
              )}
            </div>
          )}
          {error ? (
            <div className="mt-3">
              <ErrorNote>{error}</ErrorNote>
            </div>
          ) : null}
        </div>
      </div>

      {isEmpty && (
        <QuickActivities
          activities={QUICK_ACTIVITIES}
          onPick={handleQuickActivity}
          onSeeAll={() => navigate("/quick-activities")}
        />
      )}

      <Composer disabled={busy} onSend={send} onPlus={() => setMenuOpen(true)} />

      <PersistentMenuDrawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onQuickActivities={() => {
          setMenuOpen(false);
          navigate("/quick-activities");
        }}
      />
      <ThreadsDrawer
        open={threadsOpen}
        onClose={() => setThreadsOpen(false)}
        threads={threads}
        activeId={activeId}
        onPick={handlePickThread}
        onNewChat={handleNewChat}
      />
    </div>
  );
}
