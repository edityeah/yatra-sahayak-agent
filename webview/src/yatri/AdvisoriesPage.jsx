import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { Card, Badge, Loading, ErrorNote } from "../components/ui.jsx";
import { apiGet } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";

const EMPTY = { mr: "सध्या कोणत्याही सूचना नाहीत.", hi: "फ़िलहाल कोई सूचना नहीं है।", en: "No advisories right now." };

const SEVERITY_ORDER = { critical: 0, warning: 1, info: 2 };
const SEVERITY_TONE = { critical: "danger", warning: "warn", info: "default" };
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiGet(`/api/yatra/${yatra}/advisories`)
      .then((data) => {
        if (!cancelled) setAdvisories(data);
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

  const sorted = advisories
    ? [...advisories].sort(
        (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
      )
    : null;

  return (
    <div>
      <h1>{tr(strings, "advisories", language)}</h1>

      {loading ? <Loading text={tr(strings, "loading", language)} /> : null}
      {!loading && error ? <ErrorNote>{error}</ErrorNote> : null}

      {!loading && !error && sorted && sorted.length === 0 ? (
        <Card>{EMPTY[language] || EMPTY.en}</Card>
      ) : null}

      {!loading && !error && sorted
        ? sorted.map((a, i) => (
            <Card key={i} className="advisory-card">
              <div className="advisory-head">
                <Badge tone={SEVERITY_TONE[a.severity] || "default"}>
                  {t(SEVERITY_LABEL[a.severity], language) || a.severity}
                </Badge>
                <strong className="advisory-title">{t(a.title, language)}</strong>
              </div>
              <p className="advisory-body">{t(a.body, language)}</p>
              {a.issued_by ? (
                <div className="advisory-issuer">
                  {ISSUED_BY[language] || ISSUED_BY.en}: {a.issued_by}
                </div>
              ) : null}
            </Card>
          ))
        : null}
    </div>
  );
}
