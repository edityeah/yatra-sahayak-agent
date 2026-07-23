import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import QRCode from "qrcode";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";

const CAPTION = {
  mr: "चेकपॉइंटवर हा QR दाखवा — यामुळे हजेरी नोंदते आणि तुमच्या आणीबाणी माहितीशी जोडले जाते.",
  hi: "चेकपॉइंट पर यह QR दिखाएं — यह हेडकाउंट करता है और आपकी आपातकालीन जानकारी से जोड़ता है।",
  en: "Show this QR at checkpoints — it does headcount and links to your emergency details.",
};

const NO_ID = {
  mr: "पास आयडी दिलेला नाही. लिंकमध्ये ?id=<yatra_id> जोडा.",
  hi: "पास आईडी नहीं दी गई। लिंक में ?id=<yatra_id> जोड़ें।",
  en: "No pass id given. Add ?id=<yatra_id> to the link.",
};

const NOT_FOUND = {
  mr: "पास सापडला नाही.",
  hi: "पास नहीं मिला।",
  en: "Pass not found.",
};

const LABELS = {
  yatra: { mr: "यात्रा", hi: "यात्रा", en: "Yatra" },
  holder: { mr: "यात्रेकरूचे नाव", hi: "यात्री का नाम", en: "Holder Name" },
  group: { mr: "गट / दिंडी", hi: "समूह / दिंडी", en: "Group / Dindi" },
  yatraId: { mr: "यात्रा आयडी", hi: "यात्रा आईडी", en: "Yatra ID" },
};

export default function PassPage() {
  const { language } = useLang();
  const [searchParams] = useSearchParams();
  const id = searchParams.get("id");

  const [pass, setPass] = useState(null);
  const [qrDataUrl, setQrDataUrl] = useState(null);
  const [loading, setLoading] = useState(!!id);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setNotFound(false);
    apiGet(`/api/pass/${id}`)
      .then((data) => {
        if (cancelled) return;
        setPass(data);
        return QRCode.toDataURL(data.yatra_id || id);
      })
      .then((url) => {
        if (!cancelled && url) setQrDataUrl(url);
      })
      .catch((e) => {
        if (cancelled) return;
        if (String(e.message).includes("404")) {
          setNotFound(true);
        } else {
          setError(e?.message || String(e));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <PageShell title={tr(strings, "pass", language)}>
      {!id ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
          {NO_ID[language] || NO_ID.en}
        </div>
      ) : null}

      {id && loading ? (
        <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div>
      ) : null}

      {id && !loading && notFound ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
          {NOT_FOUND[language] || NOT_FOUND.en}
        </div>
      ) : null}

      {id && !loading && error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">
          {error}
        </div>
      ) : null}

      {pass && !loading && !error && !notFound ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card overflow-hidden">
          <div className="bg-primary text-white px-5 py-3">
            <div className="text-[13px] font-bold tracking-wide">{pass.yatra}</div>
          </div>
          <div className="p-5 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <div className="w-[180px] h-[180px] flex-shrink-0 rounded-xl border border-bdr bg-white flex items-center justify-center overflow-hidden">
              {qrDataUrl ? <img src={qrDataUrl} alt="Yatra QR" width={180} height={180} /> : null}
            </div>
            <dl className="flex-1 min-w-0 w-full grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-[13.5px]">
              <dt className="text-muted font-semibold">{LABELS.holder[language] || LABELS.holder.en}</dt>
              <dd className="text-ink font-bold text-right sm:text-left">{pass.name}</dd>
              <dt className="text-muted font-semibold">{LABELS.group[language] || LABELS.group.en}</dt>
              <dd className="text-ink font-bold text-right sm:text-left">{pass.group_name || "—"}</dd>
              <dt className="text-muted font-semibold">{LABELS.yatraId[language] || LABELS.yatraId.en}</dt>
              <dd className="text-ink font-mono font-bold text-right sm:text-left break-all">{pass.yatra_id}</dd>
            </dl>
          </div>
          <div className="px-5 pb-4 text-[12.5px] text-muted leading-relaxed border-t border-bdr pt-3">
            {CAPTION[language] || CAPTION.en}
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
