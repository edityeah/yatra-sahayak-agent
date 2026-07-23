import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Landmark } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { ErrorNote } from "../components/ui.jsx";
import { streamChat } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";
import Header from "../components/chat/Header.jsx";
import EmptyState from "../components/chat/EmptyState.jsx";
import QuickActivities from "../components/chat/QuickActivities.jsx";
import QuickActivitiesSheet from "../components/chat/QuickActivitiesSheet.jsx";
import Composer from "../components/chat/Composer.jsx";
import MenuDrawer from "../components/chat/MenuDrawer.jsx";
import { QUICK_ACTIVITIES } from "../data/quickActivities.js";
import { YATRA_NAMES } from "../data/yatraNames.js";

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

function newConversationId() {
  return "web-" + Date.now();
}

export default function ChatPage() {
  const { language } = useLang();
  const navigate = useNavigate();
  const ctx = useRef(getContext()).current;

  const conversationIdRef = useRef(null);
  if (conversationIdRef.current === null) {
    conversationIdRef.current = newConversationId();
  }

  const [messages, setMessages] = useState([]); // {id, role: 'user'|'bot', text}
  const [busy, setBusy] = useState(false);
  const [waitingFirstDelta, setWaitingFirstDelta] = useState(false);
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [qaOpen, setQaOpen] = useState(false);
  const scrollRef = useRef(null);
  const nextId = useRef(1);

  useEffect(() => {
    warmUpAgent();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const send = useCallback(
    async (text) => {
      const clean = String(text || "").trim();
      if (!clean || busy) return;
      setError(null);
      const userMsgId = nextId.current++;
      const botMsgId = nextId.current++;
      setMessages((prev) => [...prev, { id: userMsgId, role: "user", text: clean }]);
      setBusy(true);
      setWaitingFirstDelta(true);
      setMessages((prev) => [...prev, { id: botMsgId, role: "bot", text: "" }]);

      try {
        await streamChat(
          { user_id: ctx.user_id, conversation_id: conversationIdRef.current, text: clean },
          (chunk) => {
            setWaitingFirstDelta(false);
            setMessages((prev) => prev.map((m) => (m.id === botMsgId ? { ...m, text: m.text + chunk } : m)));
          }
        );
      } catch (e) {
        setMessages((prev) => prev.filter((m) => m.id !== botMsgId));
        setError(e?.message || String(e));
      } finally {
        setBusy(false);
        setWaitingFirstDelta(false);
      }
    },
    [busy, ctx.user_id]
  );

  function handleQuickActivity(a) {
    setQaOpen(false);
    if (a.action?.type === "route") {
      navigate(a.action.href);
      return;
    }
    send(a.action?.text || t(a.label, language));
  }

  function handleNewChat() {
    conversationIdRef.current = newConversationId();
    setMessages([]);
    setError(null);
  }

  const subtitle = t(YATRA_NAMES[ctx.yatra], language) || ctx.yatra;

  return (
    <div className="h-screen flex flex-col overflow-hidden font-sans bg-surface text-ink">
      <Header subtitle={subtitle} onMenu={() => setMenuOpen(true)} />

      <div className="flex-1 min-h-0 overflow-y-auto" ref={scrollRef}>
        <div className="max-w-3xl w-full mx-auto px-4 sm:px-6 pt-4 pb-4">
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="pt-2 space-y-3">
              {messages.map((m) => (
                <MessageBubble key={m.id} m={m} waitingFirstDelta={waitingFirstDelta} language={language} />
              ))}
            </div>
          )}
          {error ? (
            <div className="mt-3">
              <ErrorNote>{error}</ErrorNote>
            </div>
          ) : null}
        </div>
      </div>

      {messages.length === 0 && (
        <QuickActivities activities={QUICK_ACTIVITIES} onPick={handleQuickActivity} onSeeAll={() => setQaOpen(true)} />
      )}

      <Composer disabled={busy} onSend={send} onPlus={() => setQaOpen(true)} />

      <MenuDrawer open={menuOpen} onClose={() => setMenuOpen(false)} onNewChat={handleNewChat} />
      <QuickActivitiesSheet
        open={qaOpen}
        onClose={() => setQaOpen(false)}
        activities={QUICK_ACTIVITIES}
        onPick={handleQuickActivity}
      />
    </div>
  );
}
