import { useNavigate } from "react-router-dom";
import { ArrowLeft, MessageCircle } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { t } from "../lib/i18n.js";
import { QUICK_ACTIVITIES } from "../data/quickActivities.js";

const TITLE = { mr: "क्विक अ‍ॅक्टिव्हिटीज", hi: "क्विक एक्टिविटीज", en: "Quick Activities" };

// Pastel tints cycled across the grid, matching the Pravasi Setu reference
// full-page Quick Activities view.
const TINTS = [
  "bg-rose-100",
  "bg-orange-100",
  "bg-amber-100",
  "bg-sky-100",
  "bg-emerald-100",
  "bg-violet-100",
];

// Full-page grid of all Quick Activities — opened from the [+] menu's
// "Quick Activities" row and the empty-state "See all" chip. Each card
// runs its own action (send a chat turn, or navigate to a web app).
export default function QuickActivitiesPage() {
  const { language } = useLang();
  const navigate = useNavigate();

  function handlePick(a) {
    if (a.action?.type === "route") {
      navigate(a.action.href);
      return;
    }
    navigate(`/?q=${encodeURIComponent(a.action?.text || t(a.label, language))}`);
  }

  return (
    <div className="min-h-screen flex flex-col bg-surface text-ink font-sans">
      <header className="h-14 px-2 sm:px-4 flex items-center gap-2 border-b border-bdr bg-surface flex-shrink-0 sticky top-0 z-30">
        <button
          onClick={() => navigate("/")}
          className="w-10 h-10 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted flex-shrink-0"
          aria-label="Back"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="text-[14.5px] font-extrabold text-ink truncate">{t(TITLE, language)}</div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {QUICK_ACTIVITIES.map((a, i) => (
            <button
              key={a.id}
              onClick={() => handlePick(a)}
              className={`relative text-left rounded-2xl p-4 min-h-[112px] flex flex-col justify-between ${TINTS[i % TINTS.length]} hover:brightness-95 transition shadow-card`}
            >
              <div className="absolute top-3 right-3 w-7 h-7 rounded-full bg-white/70 flex items-center justify-center text-ink/60">
                <MessageCircle size={14} />
              </div>
              <div className="text-[26px]">{a.icon}</div>
              <div>
                <div className="text-[14.5px] font-extrabold text-ink pr-8">{t(a.label, language)}</div>
                <div className="text-[12px] text-ink/70 mt-0.5">{t(a.tagline, language)}</div>
              </div>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
