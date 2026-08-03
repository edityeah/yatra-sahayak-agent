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
import LocationCard from "../components/chat/LocationCard.jsx";
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
const LOC_SHARED = { mr: "📍 स्थान शेअर केले", hi: "📍 स्थान साझा किया", en: "📍 Location shared" };
const LOC_DENIED = { mr: "स्थान मिळाले नाही. कृपया शहर टाइप करा.", hi: "स्थान नहीं मिला। कृपया शहर टाइप करें।", en: "Couldn't get your location. Please type a city instead." };
const LOC_UNSUPPORTED = { mr: "या डिव्हाइसवर स्थान उपलब्ध नाही. शहर टाइप करा.", hi: "इस डिवाइस पर स्थान उपलब्ध नहीं। शहर टाइप करें।", en: "Location isn't available here. Please type a city instead." };
const SEND_FAILED = {
  mr: "उत्तर मिळाले नाही — सर्व्हर सुरू होत असावा. पुन्हा पाठवा.",
  hi: "जवाब नहीं मिला — सर्वर शुरू हो रहा होगा। दोबारा भेजें।",
  en: "No response — the server may be waking up. Please send again.",
};

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

// Tappable quick-reply chips the agent can attach to a message:
//   [[choices:Label::value||Label::value]]
const CHOICES_RE = /\[\[choices:(.*?)\]\]/;
function parseChoices(text) {
  const hit = String(text || "").match(CHOICES_RE);
  if (!hit) return { text, choices: [] };
  const choices = hit[1].split("||").map((c) => {
    const [label, value] = c.split("::");
    return { label: (label || "").trim(), value: (value || label || "").trim() };
  }).filter((c) => c.label);
  return { text: String(text).replace(CHOICES_RE, "").trim(), choices };
}

// Proactive follow-up suggestions the agent appends as a trailing line:
//   👉 You can also ask: A · B · C
// Rendered as tappable chips here; shown as plain text in SwiftChat.
const FOLLOWUP_RE = /\n*👉\s*[^:：]+[:：]\s*(.+?)\s*$/;
function parseFollowups(text) {
  const hit = String(text || "").match(FOLLOWUP_RE);
  if (!hit) return { text, choices: [] };
  const choices = hit[1].split("·").map((s) => s.trim()).filter(Boolean)
    .map((s) => ({ label: s, value: s }));
  return { text: String(text).replace(FOLLOWUP_RE, "").trim(), choices };
}

function MessageBubble({ m, waitingFirstDelta, language, onChoice }) {
  if (m.role === "user") {
    // A shared location renders as a map card (like SwiftChat's native pin),
    // not a text bubble.
    if (m.kind === "location" && typeof m.lat === "number" && typeof m.lng === "number") {
      return (
        <div className="flex justify-end">
          <LocationCard lat={m.lat} lng={m.lng} />
        </div>
      );
    }
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-user text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-card">
          <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{m.text}</p>
        </div>
      </div>
    );
  }
  const parsed = parseChoices(m.text);
  const fu = parseFollowups(parsed.text);
  const cleanText = fu.text;
  const choices = [...parsed.choices, ...fu.choices];
  const isTyping = cleanText === "" && waitingFirstDelta && choices.length === 0;
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
            <p className="text-[14px] leading-relaxed whitespace-pre-wrap">{renderMarkdown(cleanText)}</p>
          )}
        </div>
        {choices.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {choices.map((c, i) => (
              <button key={i} onClick={() => onChoice?.(c.value)}
                className="inline-flex items-center h-9 px-4 rounded-full bg-primary-50 border border-primary/30 text-primary text-[13px] font-bold hover:bg-primary-100 transition">
                {c.label}
              </button>
            ))}
          </div>
        ) : null}
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
          },
          () => setWaitingFirstDelta(true)   // server waking — keep the typing indicator
        );
        // Never render an empty bubble — an empty reply means the stream failed
        // (e.g. cold start) so surface a retry instead.
        if (full && full.trim()) {
          appendMessage(id, { role: "bot", text: full });
          setThreads(loadThreads());
        } else {
          setError(t(SEND_FAILED, language));
        }
      } catch (e) {
        setError(t(SEND_FAILED, language));
      } finally {
        setBusy(false);
        setWaitingFirstDelta(false);
        setStreamText(null);
      }
    },
    [activeId, busy, ctx.user_id, language, setLanguage]
  );

  // Share the device location natively IN THE CHAT: geolocate, drop a user
  // bubble, and POST a location message (same shape SwiftChat sends) so the
  // agent streams the route-weather card inline — no webview, no separate page.
  const sendLocation = useCallback(() => {
    if (busy) return;
    setError(null);
    if (!navigator.geolocation) { setError(t(LOC_UNSUPPORTED, language)); return; }

    let id = activeId;
    if (!id) { const th = createThread({}); id = th.id; setActiveId(id); }

    setBusy(true);
    setWaitingFirstDelta(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const location = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        appendMessage(id, { role: "user", kind: "location", lat: location.lat, lng: location.lng, text: t(LOC_SHARED, language) });
        setThreads(loadThreads());
        setStreamText("");
        try {
          const full = await streamChat(
            { user_id: ctx.user_id, conversation_id: id, location, language, yatra },
            (chunk) => { setWaitingFirstDelta(false); setStreamText((prev) => (prev || "") + chunk); },
            () => setWaitingFirstDelta(true)
          );
          if (full && full.trim()) {
            appendMessage(id, { role: "bot", text: full });
            setThreads(loadThreads());
          } else {
            setError(t(SEND_FAILED, language));
          }
        } catch (e) {
          setError(t(SEND_FAILED, language));
        } finally {
          setBusy(false); setWaitingFirstDelta(false); setStreamText(null);
        }
      },
      () => { setBusy(false); setWaitingFirstDelta(false); setError(t(LOC_DENIED, language)); },
      { timeout: 10000, enableHighAccuracy: true }
    );
  }, [activeId, busy, ctx.user_id, language, yatra]);

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
  // Only show a subtitle once a yatra is picked; the header stays just
  // "Maharashtra Yatra Sahayak" until then (no "Select your yatra" line).
  const subtitle = yatra ? t(YATRA_NAMES[yatra], language) : "";

  // A tapped quick-reply chip: if it's a yatra pick, remember it locally too.
  const onChoice = (value) => {
    if (value === "pandharpur" || value === "kumbh") setYatra(value);
    send(value);
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden font-sans bg-surface text-ink">
      <Header
        subtitle={subtitle}
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
                <MessageBubble key={i} m={m} waitingFirstDelta={false} language={language} onChoice={onChoice} />
              ))}
              {streamText !== null && (
                <MessageBubble
                  key="streaming"
                  m={{ role: "bot", text: streamText }}
                  waitingFirstDelta={waitingFirstDelta}
                  language={language}
                  onChoice={onChoice}
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
        onShareLocation={() => {
          setMenuOpen(false);
          sendLocation();
        }}
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
