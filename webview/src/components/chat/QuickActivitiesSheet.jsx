import { X, Sparkles } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const SHEET_TITLE = { mr: "क्विक अ‍ॅक्टिव्हिटीज", hi: "क्विक एक्टिविटीज", en: "Quick Activities" };
const SHEET_SUB = {
  mr: "प्रश्न विचारा किंवा साधन उघडा",
  hi: "सवाल पूछें या टूल खोलें",
  en: "Ask a question or open a tool",
};

// Full listing of Quick Activities. Opens from either the composer's [+]
// button or the "See all" chip on the quick-activities bar.
export default function QuickActivitiesSheet({ open, onClose, activities, onPick }) {
  const { language } = useLang();
  if (!open) return null;
  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-ink/50 backdrop-blur-[2px] z-40 animate-fade-in" />
      <aside className="fixed inset-y-0 right-0 z-50 w-full sm:w-[460px] bg-surface shadow-drawer animate-slide-in-right flex flex-col">
        <div className="h-14 flex items-center gap-2 px-4 border-b border-bdr flex-shrink-0">
          <div className="w-9 h-9 rounded-xl bg-primary-100 text-primary flex items-center justify-center">
            <Sparkles size={16} />
          </div>
          <div className="flex-1">
            <div className="text-[13.5px] font-extrabold text-ink">{t(SHEET_TITLE, language)}</div>
            <div className="text-[11px] text-muted">{t(SHEET_SUB, language)}</div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted"
            aria-label="Close"
          >
            <X size={17} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {activities.map((a) => (
            <button
              key={a.id}
              onClick={() => onPick(a)}
              className="w-full flex items-start gap-3 p-4 rounded-2xl border border-bdr bg-white hover:border-primary hover:bg-primary-50 transition text-left"
            >
              <div className="w-11 h-11 rounded-xl bg-primary-100 text-primary text-[22px] flex items-center justify-center flex-shrink-0">
                {a.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[14px] font-extrabold text-ink">{t(a.label, language)}</div>
                <div className="text-[12px] text-muted mt-0.5">{t(a.tagline, language)}</div>
              </div>
            </button>
          ))}
        </div>
      </aside>
    </>
  );
}
