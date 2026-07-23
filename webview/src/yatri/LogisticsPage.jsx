import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
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
    <PageShell title={tr(strings, "logistics", language)}>
      {loading ? (
        <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div>
      ) : null}
      {!loading && error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
          {error}
        </div>
      ) : null}

      {!loading && !error && items && items.length === 0 ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 text-[13.5px] text-ink">
          {EMPTY[language] || EMPTY.en}
        </div>
      ) : null}

      {!loading && !error && items && items.length > 0 ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card overflow-x-auto">
          <table className="w-full text-[13px] border-collapse min-w-[420px]">
            <thead>
              <tr className="bg-surface-2 text-left">
                <th className="px-4 py-2.5 font-bold text-ink border-b border-bdr">{HEAD_SERVICE[language] || HEAD_SERVICE.en}</th>
                <th className="px-4 py-2.5 font-bold text-ink border-b border-bdr">{HEAD_RATE[language] || HEAD_RATE.en}</th>
                <th className="px-4 py-2.5 font-bold text-ink border-b border-bdr">{HEAD_NOTE[language] || HEAD_NOTE.en}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row, i) => (
                <tr key={i} className="border-b border-bdr last:border-b-0">
                  <td className="px-4 py-2.5 text-ink font-semibold align-top">{t(row.service, language)}</td>
                  <td className="px-4 py-2.5 text-ink align-top">
                    {t(row.rate, language)}
                    {row.unit ? <span className="text-muted"> / {t(row.unit, language)}</span> : null}
                  </td>
                  <td className="px-4 py-2.5 text-muted align-top">{row.note ? t(row.note, language) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="mt-4 text-[12.5px] text-muted leading-relaxed">{FOOTER[language] || FOOTER.en}</p>
    </PageShell>
  );
}
