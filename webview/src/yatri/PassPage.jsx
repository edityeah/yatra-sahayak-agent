import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import QRCode from "qrcode";
import { Download, Share2 } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";
import { YATRA_NAMES } from "../data/yatraNames.js";
import { downloadQr, whatsappUrl, passUrl } from "../lib/passShare.js";

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
  age: { mr: "वय", hi: "उम्र", en: "Age" },
  group: { mr: "गट / दिंडी", hi: "समूह / दिंडी", en: "Group / Dindi" },
  emergency: { mr: "आपत्कालीन संपर्क", hi: "आपातकालीन संपर्क", en: "Emergency contact" },
  medical: { mr: "वैद्यकीय नोंद", hi: "चिकित्सीय जानकारी", en: "Medical notes" },
  yatraId: { mr: "यात्रा आयडी", hi: "यात्रा आईडी", en: "Yatra ID" },
};

const VERIFIED = {
  mobile: { mr: "मोबाइल पडताळला", hi: "मोबाइल सत्यापित", en: "Mobile verified" },
  ekyc: { mr: "e-KYC पडताळली", hi: "e-KYC सत्यापित", en: "e-KYC verified" },
};

const RFID = { mr: "RFID यात्रा पास", hi: "RFID यात्रा पास", en: "RFID Yatra Pass" };

// The pass is an identity document — render its labels bilingually (English /
// Marathi), like Aadhaar, regardless of the chosen UI language.
const bi = (label) => `${label.en} / ${label.mr}`;

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
        // Encode the pass URL (not the bare id) so scanning it opens the pass.
        return QRCode.toDataURL(passUrl(data.yatra_id || id, language), { width: 320, margin: 1 });
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
  }, [id, language]);

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
          <div className="bg-primary text-white px-5 py-3 flex items-center justify-between gap-2">
            <div className="text-[13px] font-bold tracking-wide">
              {YATRA_NAMES[pass.yatra]
                ? `${t(YATRA_NAMES[pass.yatra], "en")} / ${t(YATRA_NAMES[pass.yatra], "mr")}`
                : pass.yatra}
            </div>
            <div className="text-[11px] font-bold bg-white/20 rounded-full px-2.5 py-0.5">{RFID[language] || RFID.en}</div>
          </div>
          <div className="p-5 flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            <div className="flex flex-col items-center gap-2 flex-shrink-0">
              <div className="w-[180px] h-[180px] rounded-xl border border-bdr bg-white flex items-center justify-center overflow-hidden">
                {qrDataUrl ? <img src={qrDataUrl} alt="Yatra QR" width={180} height={180} /> : null}
              </div>
              <div className="flex flex-col items-stretch gap-1 w-[180px]">
                {pass.mobile_verified ? (
                  <span className="text-center text-[10.5px] font-bold text-green-700 bg-green-50 border border-green-200 rounded-lg px-2 py-0.5 leading-tight">
                    ✓ {VERIFIED.mobile.en} / {VERIFIED.mobile.mr}
                  </span>
                ) : null}
                {pass.ekyc_verified ? (
                  <span className="text-center text-[10.5px] font-bold text-green-700 bg-green-50 border border-green-200 rounded-lg px-2 py-0.5 leading-tight">
                    ✓ {VERIFIED.ekyc.en} / {VERIFIED.ekyc.mr}
                  </span>
                ) : null}
              </div>
              <div className="flex items-center gap-2 w-[180px]">
                <button
                  type="button"
                  onClick={() => downloadQr(qrDataUrl, pass.yatra_id)}
                  className="flex-1 h-9 rounded-xl border border-bdr bg-surface-2 text-ink text-[12px] font-bold flex items-center justify-center gap-1.5 hover:border-primary transition"
                >
                  <Download size={14} /> {tr(strings, "downloadQr", language)}
                </button>
                <a
                  href={whatsappUrl(pass.yatra_id, tr(strings, "shareText", language), language)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 h-9 rounded-xl bg-[#25D366] text-white text-[12px] font-bold flex items-center justify-center gap-1.5 hover:opacity-90 transition"
                >
                  <Share2 size={14} /> WhatsApp
                </a>
              </div>
            </div>
            <dl className="flex-1 min-w-0 w-full grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-[13.5px]">
              <dt className="text-muted font-semibold">{bi(LABELS.holder)}</dt>
              <dd className="text-ink font-bold text-right sm:text-left">{pass.name}</dd>
              {pass.age ? (<>
                <dt className="text-muted font-semibold">{bi(LABELS.age)}</dt>
                <dd className="text-ink font-bold text-right sm:text-left">{pass.age}</dd>
              </>) : null}
              <dt className="text-muted font-semibold">{bi(LABELS.group)}</dt>
              <dd className="text-ink font-bold text-right sm:text-left">
                {pass.group_name || "—"}{pass.group_size ? ` · ${pass.group_size}` : ""}
              </dd>
              {pass.emergency_contact ? (<>
                <dt className="text-muted font-semibold">{bi(LABELS.emergency)}</dt>
                <dd className="text-ink font-bold text-right sm:text-left break-words">{pass.emergency_contact}</dd>
              </>) : null}
              {pass.medical_flags && pass.medical_flags !== "none" ? (<>
                <dt className="text-muted font-semibold">{bi(LABELS.medical)}</dt>
                <dd className="text-ink font-bold text-right sm:text-left break-words">{pass.medical_flags}</dd>
              </>) : null}
              <dt className="text-muted font-semibold">{bi(LABELS.yatraId)}</dt>
              <dd className="text-ink font-mono font-bold text-right sm:text-left break-all">{pass.yatra_id}</dd>
            </dl>
          </div>
          <div className="px-5 pb-4 text-[12px] text-muted leading-relaxed border-t border-bdr pt-3 space-y-1">
            <div>{CAPTION.en}</div>
            <div>{CAPTION.mr}</div>
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
