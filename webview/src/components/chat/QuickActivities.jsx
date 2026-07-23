import { Sparkles } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

// The horizontal strip of Quick Activity chips shown right above the
// composer, matching the Pravasi Setu Assistant reference. Tapping a chip
// either sends its text into the chat or navigates to an in-app page.
export default function QuickActivities({ activities, onPick, onSeeAll }) {
  const { language } = useLang();
  const chips = activities.slice(0, 4);
  return (
    <div className="flex-shrink-0 border-t border-bdr-soft bg-surface-2/60">
      <div className="max-w-3xl w-full mx-auto px-4 sm:px-6 py-3">
        <div className="flex items-center gap-1.5 mb-2 text-muted">
          <Sparkles size={13} className="text-primary" />
          <span className="text-[11.5px] font-bold uppercase tracking-wider">Quick Activities</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {chips.map((a) => (
            <button
              key={a.id}
              onClick={() => onPick(a)}
              className="inline-flex items-center gap-2 h-10 px-4 rounded-full bg-white border border-bdr hover:border-primary shadow-card text-[13px] font-bold text-ink transition"
            >
              <span className="text-[15px]">{a.icon}</span>
              {t(a.label, language)}
            </button>
          ))}
          {activities.length > chips.length && (
            <button
              onClick={onSeeAll}
              className="inline-flex items-center h-10 px-3 rounded-full bg-primary-50 text-primary text-[12px] font-bold hover:bg-primary-100"
            >
              See all
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
