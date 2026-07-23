import { useEffect, useState } from "react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { Card, Loading, ErrorNote } from "../components/ui.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const EMPTY = { mr: "सराव उपलब्ध नाहीत.", hi: "अभ्यास उपलब्ध नहीं हैं।", en: "No drills available." };

function DrillCard({ drill, language }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="drill-card">
      <button type="button" className="drill-toggle" onClick={() => setOpen((o) => !o)}>
        <strong>{t(drill.title, language)}</strong>
        <span className="drill-caret">{open ? "▲" : "▼"}</span>
      </button>
      {open ? <p className="drill-body">{t(drill.body, language)}</p> : null}
    </Card>
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
    <div>
      <h1>{tr(strings, "drills", language)}</h1>

      {loading ? <Loading text={tr(strings, "loading", language)} /> : null}
      {!loading && error ? <ErrorNote>{error}</ErrorNote> : null}

      {!loading && !error && drills && drills.length === 0 ? (
        <Card>{EMPTY[language] || EMPTY.en}</Card>
      ) : null}

      {!loading && !error && drills
        ? drills.map((d) => <DrillCard key={d.id} drill={d} language={language} />)
        : null}
    </div>
  );
}
