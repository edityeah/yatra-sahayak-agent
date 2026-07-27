import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { t } from "../lib/i18n.js";
import QuickActivities from "../components/chat/QuickActivities.jsx";
import Composer from "../components/chat/Composer.jsx";
import OfficerGate, { useOfficerKey } from "./OfficerGate.jsx";
import { officerAsk } from "./officerApi.js";

// Officer quick-activities — each opens a webview activity (mirrors the yatri
// agent's chip → webview pattern).
const OFFICER_ACTIVITIES = [
  { id: "grievances", icon: "📝", label: { mr: "तक्रारी", hi: "शिकायतें", en: "Grievances" },
    tagline: { mr: "यात्रेकरूंच्या तक्रारी", hi: "यात्रियों की शिकायतें", en: "Pilgrim grievances" },
    action: { type: "route", href: "/officer/grievances" } },
  { id: "alerts", icon: "📢", label: { mr: "सूचना पाठवा", hi: "अलर्ट भेजें", en: "Alerts" },
    tagline: { mr: "यात्रेकरूंना सूचना", hi: "यात्रियों को अलर्ट", en: "Broadcast to pilgrims" },
    action: { type: "route", href: "/officer/alerts" } },
  { id: "sos", icon: "🆘", label: { mr: "SOS", hi: "SOS", en: "SOS feed" },
    tagline: { mr: "थेट आणीबाणी", hi: "लाइव आपातकाल", en: "Live emergencies" },
    action: { type: "route", href: "/officer/sos" } },
  { id: "registry", icon: "🧾", label: { mr: "नोंदणी व हरवले", hi: "पंजीकरण व खोया", en: "Registry & L&F" },
    tagline: { mr: "हजेरी व हरवले–सापडले", hi: "हेडकाउंट व खोया–पाया", en: "Headcount & lost-found" },
    action: { type: "route", href: "/officer/registry" } },
];

const HELLO = { mr: "👮 नियंत्रण कक्ष. सारांश, SOS, तक्रारी, हरवले–सापडले विचारा किंवा यात्रेकरू शोधा — किंवा वरील मॉड्यूल उघडा.",
                hi: "👮 नियंत्रण कक्ष। सारांश, SOS, शिकायतें, खोया–पाया पूछें या यात्री खोजें — या ऊपर के मॉड्यूल खोलें।",
                en: "👮 Control room. Ask me for a summary, SOS, grievances, lost & found, or to find a pilgrim — or open a module above." };

function clean(txt) { return (txt || "").replace(/\*\*/g, "").replace(/`/g, ""); }

function OfficerChatInner() {
  const key = useOfficerKey();
  const { language } = useLang();
  const navigate = useNavigate();
  const [msgs, setMsgs] = useState([]);
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async (text) => {
    const q = String(text || "").trim();
    if (!q || busy) return;
    setMsgs((m) => [...m, { role: "user", text: q }]); setBusy(true);
    try { const r = await officerAsk(q, key); setMsgs((m) => [...m, { role: "bot", text: clean(r) }]); }
    catch (e) { setMsgs((m) => [...m, { role: "bot", text: `Error: ${e?.message || e}` }]); }
    finally { setBusy(false); }
  };
  const pick = (a) => a.action?.type === "route" && navigate(a.action.href);
  const isEmpty = msgs.length === 0;

  return (
    <>
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-3xl w-full mx-auto px-4 pt-4 pb-4">
          {isEmpty ? (
            <div className="flex flex-col items-center text-center py-10">
              <div className="w-20 h-20 rounded-full bg-primary-100 text-primary flex items-center justify-center"><ShieldCheck size={34} /></div>
              <p className="mt-4 text-[15px] font-extrabold text-ink max-w-sm">{t(HELLO, language)}</p>
            </div>
          ) : (
            <div className="space-y-3 pt-2">
              {msgs.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : "flex"}>
                  <div className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-[14px] whitespace-pre-wrap shadow-card ${m.role === "user" ? "bg-user text-white rounded-br-md" : "bg-white text-ink border border-bdr-soft rounded-tl-md"}`}>{m.text}</div>
                </div>
              ))}
              {busy ? <div className="text-[13px] text-muted italic px-1">…</div> : null}
              <div ref={endRef} />
            </div>
          )}
        </div>
      </div>
      {isEmpty ? <QuickActivities activities={OFFICER_ACTIVITIES} onPick={pick} onSeeAll={null} /> : null}
      <Composer disabled={busy} onSend={send} onPlus={null} />
    </>
  );
}

export default function OfficerChatPage() {
  return (
    <OfficerGate title="Yatra Officer — Control Room" subtitle="Ops assistant">
      <OfficerChatInner />
    </OfficerGate>
  );
}
