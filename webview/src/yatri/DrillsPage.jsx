import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const EMPTY = { mr: "सराव उपलब्ध नाहीत.", hi: "अभ्यास उपलब्ध नहीं हैं।", en: "No drills available." };

function DrillCard({ drill, language }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-2xl border border-bdr bg-surface shadow-card overflow-hidden">
      <button
        type="button"
        className="w-full flex items-center justify-between gap-3 px-4 py-3.5 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="text-[13.5px] font-bold text-ink">{t(drill.title, language)}</span>
        {open ? (
          <ChevronUp size={16} className="text-muted flex-shrink-0" />
        ) : (
          <ChevronDown size={16} className="text-muted flex-shrink-0" />
        )}
      </button>
      {open ? (
        <p className="px-4 pb-4 text-[13px] text-muted leading-relaxed border-t border-bdr pt-3">
          {t(drill.body, language)}
        </p>
      ) : null}
    </div>
  );
}

export default function DrillsPage() {
  const { language } = useLang();
  const [drills, setDrills] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiGet("/api/drills")
      .then((data) => {
        if (!cancelled) setDrills(data);
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
  }, []);

  return (
    <PageShell title={tr(strings, "drills", language)}>
      {loading ? (
        <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div>
      ) : null}
      {!loading && error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
          {error}
        </div>
      ) : null}

      {!loading && !error && drills && drills.length === 0 ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 text-[13.5px] text-ink">
          {EMPTY[language] || EMPTY.en}
        </div>
      ) : null}

      {!loading && !error && drills ? (
        <div className="space-y-3">
          {drills.map((d) => (
            <DrillCard key={d.id} drill={d} language={language} />
          ))}
        </div>
      ) : null}
    </PageShell>
  );
}
