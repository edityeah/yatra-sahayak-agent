import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";

const EMPTY = { mr: "सध्या कोणत्याही सूचना नाहीत.", hi: "फ़िलहाल कोई सूचना नहीं है।", en: "No advisories right now." };

const SEVERITY_ORDER = { critical: 0, warning: 1, info: 2 };
const SEVERITY_STYLE = {
  critical: "bg-red-50 text-red-700 border-red-200",
  warning: "bg-amber-50 text-amber-800 border-amber-200",
  info: "bg-primary-50 text-primary border-primary-200",
};
const SEVERITY_LABEL = {
  critical: { mr: "गंभीर", hi: "गंभीर", en: "Critical" },
  warning: { mr: "इशारा", hi: "चेतावनी", en: "Warning" },
  info: { mr: "माहिती", hi: "जानकारी", en: "Info" },
};
const ISSUED_BY = { mr: "जारीकर्ता", hi: "जारीकर्ता", en: "Issued by" };

export default function AdvisoriesPage() {
  const { language } = useLang();
  const [searchParams] = useSearchParams();
  const ctx = getContext();
  const yatra = searchParams.get("yatra") || ctx.yatra;

  const [advisories, setAdvisories] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      apiGet(`/api/yatra/${yatra}/advisories`),
      apiGet(`/api/alerts?yatra=${yatra}`).catch(() => []),  // live officer alerts
    ])
      .then(([adv, al]) => {
        if (cancelled) return;
        setAdvisories(adv);
        setAlerts(al || []);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [yatra]);

  const ALERT_STYLE = {
    danger: "bg-red-50 text-red-700 border-red-200",
    warning: "bg-amber-50 text-amber-800 border-amber-200",
    info: "bg-primary-50 text-primary border-primary-200",
  };
  const LIVE = { mr: "थेट सूचना", hi: "लाइव अलर्ट", en: "Live alert" };

  const sorted = advisories
    ? [...advisories].sort(
        (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
      )
    : null;

  return (
    <PageShell title={tr(strings, "advisories", language)}>
      {loading ? (
        <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div>
      ) : null}
      {!loading && error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
          {error}
        </div>
      ) : null}

      {!loading && !error && alerts.length > 0 ? (
        <div className="space-y-3 mb-3">
          {alerts.map((a) => (
            <div key={a.id} className={`rounded-2xl border shadow-card p-4 ${ALERT_STYLE[a.severity] || ALERT_STYLE.info}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-white/70 border border-current uppercase tracking-wide">
                  📢 {t(LIVE, language)}
                </span>
                <strong className="text-[13.5px] font-extrabold">{a.title}</strong>
              </div>
              <p className="text-[13px] leading-relaxed">{a.message}</p>
            </div>
          ))}
        </div>
      ) : null}

      {!loading && !error && sorted && sorted.length === 0 && alerts.length === 0 ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 text-[13.5px] text-ink">
          {EMPTY[language] || EMPTY.en}
        </div>
      ) : null}

      {!loading && !error && sorted ? (
        <div className="space-y-3">
          {sorted.map((a, i) => (
            <div key={i} className="rounded-2xl border border-bdr bg-surface shadow-card p-4">
              <div className="flex items-center gap-2 mb-1.5">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold border ${
                    SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.info
                  }`}
                >
                  {t(SEVERITY_LABEL[a.severity], language) || a.severity}
                </span>
                <strong className="text-[13.5px] font-bold text-ink">{t(a.title, language)}</strong>
              </div>
              <p className="text-[13px] text-ink leading-relaxed">{t(a.body, language)}</p>
              {a.issued_by ? (
                <div className="mt-2 text-[12px] text-muted">
                  {ISSUED_BY[language] || ISSUED_BY.en}: {a.issued_by}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </PageShell>
  );
}
