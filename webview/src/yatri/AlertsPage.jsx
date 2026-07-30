import { useCallback, useEffect, useState } from "react";
import { Megaphone, AlertTriangle, Info, ShieldAlert, RefreshCw, Landmark } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";
import { YATRA_NAMES } from "../data/yatraNames.js";

const TITLE = { mr: "सूचना / अलर्ट", hi: "सूचनाएँ / अलर्ट", en: "Alerts" };
const FROM = { mr: "यात्रा नियंत्रण कक्ष / आपत्कालीन नियंत्रण केंद्राकडून जारी",
               hi: "यात्रा नियंत्रण कक्ष / आपातकालीन नियंत्रण केंद्र द्वारा जारी",
               en: "Issued by the Yatra control room / State Emergency Control Centre" };
const EMPTY = { mr: "सध्या कोणतीही सक्रिय सूचना नाही. सुरक्षित रहा! 🙏",
                hi: "अभी कोई सक्रिय अलर्ट नहीं। सुरक्षित रहें! 🙏",
                en: "No active alerts right now. Stay safe! 🙏" };
const FAILED = { mr: "सूचना लोड करता आल्या नाहीत — पुन्हा प्रयत्न करा.", hi: "अलर्ट लोड नहीं हुए — फिर से कोशिश करें।", en: "Couldn't load alerts — try again." };
const RETRY = { mr: "पुन्हा प्रयत्न करा", hi: "फिर से कोशिश करें", en: "Retry" };
const OFFICIAL = { mr: "अधिकृत", hi: "आधिकारिक", en: "Official" };

// severity → { style, icon, label }
const SEV = {
  critical: { ring: "border-red-300 bg-red-50", dot: "bg-red-500", text: "text-red-700", icon: ShieldAlert, label: { mr: "अत्यावश्यक", hi: "अत्यावश्यक", en: "Critical" } },
  danger: { ring: "border-red-300 bg-red-50", dot: "bg-red-500", text: "text-red-700", icon: ShieldAlert, label: { mr: "धोका", hi: "खतरा", en: "Danger" } },
  warning: { ring: "border-amber-300 bg-amber-50", dot: "bg-amber-500", text: "text-amber-800", icon: AlertTriangle, label: { mr: "इशारा", hi: "चेतावनी", en: "Warning" } },
  info: { ring: "border-primary/30 bg-primary-50", dot: "bg-primary", text: "text-primary", icon: Info, label: { mr: "माहिती", hi: "सूचना", en: "Info" } },
};
const sevOf = (s) => SEV[s] || SEV.info;

export default function AlertsPage() {
  const { language, yatra } = useLang();
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setError(false); setAlerts(null);
    try {
      const q = yatra ? `?yatra=${encodeURIComponent(yatra)}` : "";
      const rows = await apiGet(`/api/alerts${q}`);
      setAlerts(Array.isArray(rows) ? rows : []);
    } catch (e) {
      setError(true);
    }
  }, [yatra]);
  useEffect(() => { load(); }, [load, reloadKey]);

  return (
    <PageShell title={t(TITLE, language)}>
      <div className="flex items-center gap-2 text-[12px] text-muted mb-3">
        <Landmark size={14} className="text-primary flex-shrink-0" />
        <span>{t(FROM, language)}{yatra ? ` · ${t(YATRA_NAMES[yatra] || {}, language)}` : ""}</span>
      </div>

      {error ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 text-amber-800 text-[13.5px] px-4 py-3 flex items-center justify-between gap-3">
          <span>{t(FAILED, language)}</span>
          <button onClick={() => setReloadKey((k) => k + 1)} className="flex-shrink-0 h-9 px-4 rounded-full bg-primary text-white text-[13px] font-bold inline-flex items-center gap-1.5 hover:bg-primary-700 transition">
            <RefreshCw size={13} /> {t(RETRY, language)}
          </button>
        </div>
      ) : alerts === null ? (
        <div className="text-[13.5px] text-muted px-1 py-3">…</div>
      ) : alerts.length === 0 ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-6 text-center">
          <Megaphone size={26} className="mx-auto text-muted mb-2" />
          <div className="text-[14px] text-ink">{t(EMPTY, language)}</div>
        </div>
      ) : (
        <div className="space-y-2.5">
          {alerts.map((a) => {
            const s = sevOf(a.severity);
            const Icon = s.icon;
            return (
              <div key={a.id} className={`rounded-2xl border shadow-card p-4 ${s.ring}`}>
                <div className="flex items-start gap-3">
                  <span className={`w-9 h-9 rounded-full ${s.dot} text-white flex items-center justify-center flex-shrink-0`}><Icon size={18} /></span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[15px] font-extrabold ${s.text}`}>{a.title || "—"}</span>
                      <span className={`text-[10px] font-bold uppercase tracking-wide ${s.text}`}>· {t(s.label, language)}</span>
                    </div>
                    <p className="text-[13.5px] text-ink mt-1 leading-relaxed whitespace-pre-wrap">{a.message}</p>
                    <div className="text-[11px] text-muted mt-2 flex items-center gap-1">
                      <ShieldAlert size={11} /> {t(OFFICIAL, language)} · {String(a.id)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </PageShell>
  );
}
