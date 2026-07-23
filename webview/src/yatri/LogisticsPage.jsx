import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { Card, Loading, ErrorNote } from "../components/ui.jsx";
import { apiGet } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";
import { t } from "../lib/i18n.js";

const HEAD_SERVICE = { mr: "सेवा", hi: "सेवा", en: "Service" };
const HEAD_RATE = { mr: "दर / एकक", hi: "दर / इकाई", en: "Rate / Unit" };
const HEAD_NOTE = { mr: "टीप", hi: "टिप्पणी", en: "Note" };
const EMPTY = { mr: "या यात्रेसाठी सुविधा दर उपलब्ध नाहीत.", hi: "इस यात्रा के लिए सुविधा दरें उपलब्ध नहीं हैं।", en: "No logistics rates available for this yatra." };
const FOOTER = {
  mr: "जास्त पैसे आकारले जात आहेत? नियंत्रण कक्षाला कळवा.",
  hi: "ज़्यादा पैसे लिए जा रहे हैं? कंट्रोल रूम को सूचित करें।",
  en: "Being overcharged? Report it via the control room.",
};

export default function LogisticsPage() {
  const { language } = useLang();
  const [searchParams] = useSearchParams();
  const ctx = getContext();
  const yatra = searchParams.get("yatra") || ctx.yatra;

  const [items, setItems] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    apiGet(`/api/yatra/${yatra}/logistics`)
      .then((data) => {
        if (!cancelled) setItems(data);
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

  return (
    <div>
      <h1>{tr(strings, "logistics", language)}</h1>

      {loading ? <Loading text={tr(strings, "loading", language)} /> : null}
      {!loading && error ? <ErrorNote>{error}</ErrorNote> : null}

      {!loading && !error && items && items.length === 0 ? (
        <Card>{EMPTY[language] || EMPTY.en}</Card>
      ) : null}

      {!loading && !error && items && items.length > 0 ? (
        <div className="table-wrap">
          <table className="rate-table">
            <thead>
              <tr>
                <th>{HEAD_SERVICE[language] || HEAD_SERVICE.en}</th>
                <th>{HEAD_RATE[language] || HEAD_RATE.en}</th>
                <th>{HEAD_NOTE[language] || HEAD_NOTE.en}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row, i) => (
                <tr key={i}>
                  <td>{t(row.service, language)}</td>
                  <td>
                    {t(row.rate, language)}
                    {row.unit ? <span className="rate-unit"> / {t(row.unit, language)}</span> : null}
                  </td>
                  <td>{row.note ? t(row.note, language) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="page-footer-note">{FOOTER[language] || FOOTER.en}</p>
    </div>
  );
}
