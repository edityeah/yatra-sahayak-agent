import { Camera, Image as ImageIcon, FileText, Sparkles, X } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const CAMERA = { mr: "कॅमेरा", hi: "कैमरा", en: "Camera" };
const GALLERY = { mr: "गॅलरी", hi: "गैलरी", en: "Gallery" };
const DOCUMENT = { mr: "दस्तऐवज", hi: "दस्तावेज़", en: "Document" };
const QUICK_ACTIVITIES = { mr: "क्विक अ‍ॅक्टिव्हिटीज", hi: "क्विक एक्टिविटीज", en: "Quick Activities" };
const COMING_SOON = { mr: "लवकरच येत आहे", hi: "जल्द आ रहा है", en: "Coming soon" };
const NEW_BADGE = { mr: "नवीन", hi: "नया", en: "New" };

// Right slide-in drawer opened by the composer's [+] button — matches the
// Pravasi Setu persistent menu (Camera / Gallery / Document / Quick
// Activities). Camera/Gallery/Document are stubs; Quick Activities routes
// to the full-page grid.
export default function PersistentMenuDrawer({ open, onClose, onQuickActivities }) {
  const { language } = useLang();
  if (!open) return null;

  const items = [
    { icon: Camera, label: CAMERA, onClick: () => window.alert(t(COMING_SOON, language)) },
    { icon: ImageIcon, label: GALLERY, onClick: () => window.alert(t(COMING_SOON, language)) },
    { icon: FileText, label: DOCUMENT, onClick: () => window.alert(t(COMING_SOON, language)) },
    { icon: Sparkles, label: QUICK_ACTIVITIES, onClick: onQuickActivities, badge: NEW_BADGE },
  ];

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-ink/50 backdrop-blur-[2px] z-40 animate-fade-in" />
      <aside className="fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] bg-surface shadow-drawer animate-slide-in-right flex flex-col">
        <div className="h-14 flex items-center px-4 flex-shrink-0">
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted"
            aria-label="Close"
          >
            <X size={17} />
          </button>
        </div>
        <div className="px-5 py-2 space-y-2 flex-1 overflow-y-auto">
          {items.map((it) => {
            const Icon = it.icon;
            return (
              <button
                key={t(it.label, "en")}
                onClick={it.onClick}
                className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl border border-bdr hover:border-primary hover:bg-primary-50 transition text-left"
              >
                <Icon size={18} className="text-primary flex-shrink-0" />
                <span className="flex-1 text-[14px] font-bold text-primary">{t(it.label, language)}</span>
                {it.badge && (
                  <span className="text-[9.5px] font-extrabold text-white bg-gradient-to-r from-pink-500 to-red-500 rounded-full px-2 py-0.5">
                    {t(it.badge, language)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </aside>
    </>
  );
}
