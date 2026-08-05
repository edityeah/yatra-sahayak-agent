import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { ExternalLink } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import PageShell from "../components/PageShell.jsx";
import { t } from "../lib/i18n.js";

// Scan-to-open the official Solapur Police GPS parking + route map for the Wari,
// so a pilgrim can move it to another phone or share it with fellow travellers.
const ROUTE_URL = "https://solapurpolice.gov.in/ashadhi-wari";

const TITLE = { mr: "मार्ग व वाहनतळ QR", hi: "मार्ग व पार्किंग QR", en: "Route & parking QR" };
const HELP = {
  mr: "हा QR स्कॅन करा — GPS मार्गदर्शनासह अधिकृत वाहनतळ व मार्ग नकाशा उघडेल.",
  hi: "यह QR स्कैन करें — GPS नेविगेशन सहित आधिकारिक पार्किंग व रूट मैप खुलेगा।",
  en: "Scan this QR to open the official GPS-guided parking & route map.",
};
const OPEN = { mr: "थेट उघडा", hi: "सीधे खोलें", en: "Open directly" };
const SRC = {
  mr: "स्रोत: सोलापूर पोलीस (आषाढी वारी)",
  hi: "स्रोत: सोलापुर पुलिस (आषाढी वारी)",
  en: "Source: Solapur Police (Ashadhi Wari)",
};

export default function RouteQrPage() {
  const { language } = useLang();
  const [qr, setQr] = useState(null);

  useEffect(() => {
    QRCode.toDataURL(ROUTE_URL, { width: 320, margin: 1 }).then(setQr).catch(() => setQr(null));
  }, []);

  return (
    <PageShell title={t(TITLE, language)}>
      <div className="max-w-sm mx-auto text-center">
        <p className="text-[13.5px] text-ink px-2 mb-4">{t(HELP, language)}</p>
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-5 inline-block">
          {qr ? <img src={qr} alt="Route QR" className="w-56 h-56 mx-auto" /> :
            <div className="w-56 h-56 mx-auto flex items-center justify-center text-muted text-sm">…</div>}
        </div>
        <a href={ROUTE_URL} target="_blank" rel="noopener"
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-primary text-white text-[14px] font-bold px-5 h-11 hover:bg-primary-700 transition">
          <ExternalLink size={16} /> {t(OPEN, language)}
        </a>
        <p className="text-[11.5px] text-muted mt-4">{t(SRC, language)}</p>
      </div>
    </PageShell>
  );
}
