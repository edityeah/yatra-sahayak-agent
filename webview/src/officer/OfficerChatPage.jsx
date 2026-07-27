import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Menu } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { t } from "../lib/i18n.js";
import QuickActivities from "../components/chat/QuickActivities.jsx";
import Composer from "../components/chat/Composer.jsx";
import ThreadsDrawer from "../components/chat/ThreadsDrawer.jsx";
import PersistentMenuDrawer from "../components/chat/PersistentMenuDrawer.jsx";
import { makeThreadStore } from "../store/threads.js";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { officerAsk } from "./officerApi.js";

// Officer chat threads live in their own namespace (separate from the yatri
// agent's history).
const store = makeThreadStore("ysahayak.officer");

const OFFICER_ACTIVITIES = [
  { id: "grievances", icon: "📝", label: { mr: "तक्रारी", hi: "शिकायतें", en: "Grievances" }, action: { type: "route", href: "/officer/grievances" } },
  { id: "alerts", icon: "📢", label: { mr: "सूचना पाठवा", hi: "अलर्ट भेजें", en: "Alerts" }, action: { type: "route", href: "/officer/alerts" } },
  { id: "sos", icon: "🆘", label: { mr: "SOS", hi: "SOS", en: "SOS feed" }, action: { type: "route", href: "/officer/sos" } },
  { id: "registry", icon: "🧾", label: { mr: "नोंदणी व हरवले", hi: "पंजीकरण", en: "Registry & L&F" }, action: { type: "route", href: "/officer/registry" } },
];
const HELLO = { mr: "👮 नियंत्रण कक्ष. सारांश, SOS, तक्रारी, हरवले–सापडले विचारा किंवा यात्रेकरू शोधा — किंवा वरील मॉड्यूल उघडा.",
                hi: "👮 नियंत्रण कक्ष। सारांश, SOS, शिकायतें, खोया–पाया पूछें या यात्री खोजें — या ऊपर के मॉड्यूल खोलें।",
                en: "👮 Control room. Ask me for a summary, SOS, grievances, lost & found, or to find a pilgrim — or open a module above." };
const LANG_LABEL = { mr: "मरा", hi: "हिं", en: "EN" };
const clean = (x) => (x || "").replace(/\*\*/g, "").replace(/`/g, "");

function Inner() {
  const key = useOfficerKey();
  const { language, setLanguage } = useLang();
  const navigate = useNavigate();
  const [threads, setThreads] = useState(() => store.loadThreads());
  const [activeId, setActiveId] = useState(() => store.loadActiveId());
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [threadsOpen, setThreadsOpen] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => store.subscribe(() => { setThreads(store.loadThreads()); setActiveId(store.loadActiveId()); }), []);
  const activeThread = activeId ? threads[activeId] : null;
  const messages = activeThread?.messages || [];
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages, busy]);

  const send = useCallback(async (text) => {
    const q = String(text || "").trim();
    if (!q || busy) return;
    let id = activeId;
    if (!id) { const th = store.createThread({}); id = th.id; setActiveId(id); }
    store.appendMessage(id, { role: "user", text: q }); setThreads(store.loadThreads());
    setBusy(true);
    try { const r = await officerAsk(q, key); store.appendMessage(id, { role: "bot", text: clean(r) }); }
    catch (e) { store.appendMessage(id, { role: "bot", text: `Error: ${e?.message || e}` }); }
    finally { setThreads(store.loadThreads()); setBusy(false); }
  }, [activeId, busy, key]);

  const pickThread = (tid) => { store.saveActiveId(tid); setActiveId(tid); setThreadsOpen(false); };
  const newChat = () => { const th = store.createThread({}); setThreads(store.loadThreads()); setActiveId(th.id); setThreadsOpen(false); };
  const pickActivity = (a) => a.action?.type === "route" && navigate(a.action.href);
  const isEmpty = messages.length === 0;

  return (
    <div className="h-screen flex flex-col overflow-hidden font-sans bg-surface text-ink">
      <header className="h-14 px-3 sm:px-4 flex items-center gap-2 border-b border-bdr bg-surface flex-shrink-0 sticky top-0 z-30">
        <div className="w-9 h-9 rounded-full bg-primary-100 text-primary flex items-center justify-center"><ShieldCheck size={17} /></div>
        <div className="flex-1 min-w-0 leading-tight">
          <div className="text-[14.5px] font-extrabold text-ink truncate">Yatra Officer — Control Room</div>
          <div className="text-[11px] text-muted truncate">Ops assistant</div>
        </div>
        <div className="flex items-center gap-0.5 bg-surface-2 rounded-full p-0.5 mr-1">
          {["mr", "hi", "en"].map((l) => (
            <button key={l} onClick={() => setLanguage(l)} className={`px-2 h-7 rounded-full text-[11px] font-bold transition ${language === l ? "bg-primary text-white" : "text-muted hover:text-ink"}`}>{LANG_LABEL[l]}</button>
          ))}
        </div>
        <button onClick={() => setThreadsOpen(true)} className="w-10 h-10 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted" aria-label="Open menu"><Menu size={18} /></button>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto" ref={scrollRef}>
        <div className="max-w-3xl w-full mx-auto px-4 sm:px-6 pt-4 pb-4">
          {isEmpty ? (
            <div className="flex flex-col items-center text-center py-10">
              <div className="w-20 h-20 rounded-full bg-primary-100 text-primary flex items-center justify-center"><ShieldCheck size={34} /></div>
              <p className="mt-4 text-[15px] font-extrabold text-ink max-w-sm">{t(HELLO, language)}</p>
            </div>
          ) : (
            <div className="space-y-3 pt-2">
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : "flex"}>
                  <div className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-[14px] whitespace-pre-wrap shadow-card ${m.role === "user" ? "bg-user text-white rounded-br-md" : "bg-white text-ink border border-bdr-soft rounded-tl-md"}`}>{m.text}</div>
                </div>
              ))}
              {busy ? <div className="text-[13px] text-muted italic px-1">…</div> : null}
            </div>
          )}
        </div>
      </div>

      {isEmpty ? <QuickActivities activities={OFFICER_ACTIVITIES} onPick={pickActivity} onSeeAll={null} /> : null}
      <Composer disabled={busy} onSend={send} onPlus={() => setMenuOpen(true)} />

      <PersistentMenuDrawer open={menuOpen} onClose={() => setMenuOpen(false)} onQuickActivities={() => setMenuOpen(false)} />
      <ThreadsDrawer open={threadsOpen} onClose={() => setThreadsOpen(false)} threads={threads} activeId={activeId}
        onPick={pickThread} onNewChat={newChat} onDelete={store.deleteThread} />
    </div>
  );
}

export default function OfficerChatPage() {
  return <OfficerGate bare><Inner /></OfficerGate>;
}
