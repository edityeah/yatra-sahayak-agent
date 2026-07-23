import { X, IdCard, Map, Truck, ShieldAlert, Megaphone, PhoneCall, MessageSquarePlus } from "lucide-react";
import { Link } from "react-router-dom";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const LANGS = ["mr", "hi", "en"];
const LANG_LABEL = { mr: "मराठी", hi: "हिंदी", en: "English" };

const MENU_TITLE = { mr: "मेनू", hi: "मेनू", en: "Menu" };
const LANG_SECTION = { mr: "भाषा", hi: "भाषा", en: "Language" };
const APPS_SECTION = { mr: "वेब अ‍ॅप्स", hi: "वेब ऐप्स", en: "Web apps" };
const NEW_CHAT = { mr: "नवीन गप्पा", hi: "नई चैट", en: "New chat" };

const WEB_APPS = [
  { href: "/yatri/pass", icon: IdCard, label: { mr: "यात्रा पास", hi: "यात्रा पास", en: "Yatra Pass" } },
  { href: "/yatri/map", icon: Map, label: { mr: "मार्ग नकाशा", hi: "मार्ग मानचित्र", en: "Route Map" } },
  { href: "/yatri/logistics", icon: Truck, label: { mr: "सुविधा व दर", hi: "सुविधाएं व दरें", en: "Logistics & Rates" } },
  { href: "/yatri/drills", icon: ShieldAlert, label: { mr: "सुरक्षा व सराव", hi: "सुरक्षा व अभ्यास", en: "Safety & Drills" } },
  { href: "/yatri/advisories", icon: Megaphone, label: { mr: "सूचना", hi: "सूचनाएं", en: "Advisories" } },
  { href: "/voice", icon: PhoneCall, label: { mr: "व्हॉइस कॉल", hi: "वॉइस कॉल", en: "Voice Call" } },
];

// Right slide-in drawer opened from the header hamburger — language
// switcher, links to the other yatri web apps, and "New chat".
export default function MenuDrawer({ open, onClose, onNewChat }) {
  const { language, setLanguage } = useLang();
  if (!open) return null;

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-ink/50 backdrop-blur-[2px] z-40 animate-fade-in" />
      <aside className="fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] bg-surface shadow-drawer animate-slide-in-right flex flex-col">
        <div className="h-14 flex items-center px-4 flex-shrink-0 border-b border-bdr">
          <div className="flex-1 text-[13.5px] font-extrabold text-ink">{t(MENU_TITLE, language)}</div>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted"
            aria-label="Close"
          >
            <X size={17} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-6 flex-1 overflow-y-auto">
          <section>
            <div className="text-[11px] font-bold uppercase tracking-wider text-muted mb-2">
              {t(LANG_SECTION, language)}
            </div>
            <div className="flex items-center gap-2">
              {LANGS.map((l) => (
                <button
                  key={l}
                  onClick={() => setLanguage(l)}
                  className={`flex-1 h-10 rounded-xl text-[13px] font-bold border transition ${
                    l === language
                      ? "bg-primary text-white border-primary"
                      : "bg-white text-ink border-bdr hover:border-primary"
                  }`}
                >
                  {LANG_LABEL[l]}
                </button>
              ))}
            </div>
          </section>

          <section>
            <div className="text-[11px] font-bold uppercase tracking-wider text-muted mb-2">
              {t(APPS_SECTION, language)}
            </div>
            <div className="space-y-2">
              {WEB_APPS.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    to={{ pathname: item.href, search: `?lang=${language}` }}
                    onClick={onClose}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl border border-bdr hover:border-primary hover:bg-primary-50 transition text-left"
                  >
                    <Icon size={18} className="text-primary flex-shrink-0" />
                    <span className="flex-1 text-[13.5px] font-bold text-ink">{t(item.label, language)}</span>
                  </Link>
                );
              })}
            </div>
          </section>

          <section>
            <button
              onClick={() => {
                onNewChat?.();
                onClose();
              }}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl border border-bdr hover:border-primary hover:bg-primary-50 transition text-left"
            >
              <MessageSquarePlus size={18} className="text-primary flex-shrink-0" />
              <span className="flex-1 text-[14px] font-bold text-primary">{t(NEW_CHAT, language)}</span>
            </button>
          </section>
        </div>
      </aside>
    </>
  );
}
