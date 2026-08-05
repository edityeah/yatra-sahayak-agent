import { ExternalLink, Image as ImageIcon } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import PageShell from "../components/PageShell.jsx";
import { t } from "../lib/i18n.js";

// Photo gallery. We link out to the OFFICIAL Solapur Police Wari gallery rather
// than re-hosting government photographs (copyright + freshness).
const GALLERY_URL = "https://solapurpolice.gov.in/ashadhi-wari";

const TITLE = { mr: "छायाचित्र दालन", hi: "फोटो गैलरी", en: "Photo gallery" };
const BODY = {
  mr: "मागील वारीची अधिकृत छायाचित्रे सोलापूर पोलिसांच्या संकेतस्थळावर पाहा.",
  hi: "पिछली वारी की आधिकारिक तस्वीरें सोलापुर पुलिस की वेबसाइट पर देखें।",
  en: "View official photographs from past Waris on the Solapur Police website.",
};
const OPEN = { mr: "दालन उघडा", hi: "गैलरी खोलें", en: "Open gallery" };

export default function GalleryPage() {
  const { language } = useLang();
  return (
    <PageShell title={t(TITLE, language)}>
      <div className="max-w-md mx-auto text-center py-6">
        <div className="w-16 h-16 rounded-2xl bg-primary-50 text-primary flex items-center justify-center mx-auto mb-4">
          <ImageIcon size={30} />
        </div>
        <p className="text-[14px] text-ink px-3">{t(BODY, language)}</p>
        <a href={GALLERY_URL} target="_blank" rel="noopener"
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-primary text-white text-[14px] font-bold px-5 h-11 hover:bg-primary-700 transition">
          <ExternalLink size={16} /> {t(OPEN, language)}
        </a>
      </div>
    </PageShell>
  );
}
