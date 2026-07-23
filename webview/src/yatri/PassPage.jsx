import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import QRCode from "qrcode";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { Card, Loading, ErrorNote } from "../components/ui.jsx";
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
    <div>
      <h1>{tr(strings, "pass", language)}</h1>

      {!id ? <ErrorNote>{NO_ID[language] || NO_ID.en}</ErrorNote> : null}
      {id && loading ? <Loading text={tr(strings, "loading", language)} /> : null}
      {id && !loading && notFound ? <ErrorNote>{NOT_FOUND[language] || NOT_FOUND.en}</ErrorNote> : null}
      {id && !loading && error ? <ErrorNote>{error}</ErrorNote> : null}

      {pass && !loading && !error && !notFound ? (
        <Card className="pass-card">
          <div className="pass-card-header">
            <div className="pass-card-yatra">{pass.yatra}</div>
          </div>
          <div className="pass-card-body">
            <div className="pass-qr">
              {qrDataUrl ? <img src={qrDataUrl} alt="Yatra QR" width={180} height={180} /> : null}
            </div>
            <dl className="pass-details">
              <dt>{LABELS.holder[language] || LABELS.holder.en}</dt>
              <dd>{pass.name}</dd>
              <dt>{LABELS.group[language] || LABELS.group.en}</dt>
              <dd>{pass.group_name || "—"}</dd>
              <dt>{LABELS.yatraId[language] || LABELS.yatraId.en}</dt>
              <dd className="pass-yatra-id">{pass.yatra_id}</dd>
            </dl>
          </div>
          <div className="pass-card-caption">{CAPTION[language] || CAPTION.en}</div>
        </Card>
      ) : null}
    </div>
  );
}
