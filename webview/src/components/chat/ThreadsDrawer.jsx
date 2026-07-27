import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare, Settings as SettingsIcon, Plus, Trash2, X, Phone, ChevronRight } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";
import { deleteThread, groupByRecency } from "../../store/threads.js";

const TAB_CHATS = { mr: "गप्पा", hi: "चैट", en: "Chats" };
const TAB_SETTINGS = { mr: "सेटिंग्ज", hi: "सेटिंग्स", en: "Settings" };
const NEW_CHAT = { mr: "+ नवीन गप्पा", hi: "+ नई चैट", en: "+ New Chat" };
const EMPTY = { mr: "अजून गप्पा नाहीत.", hi: "अभी तक कोई चैट नहीं।", en: "No chats yet." };
const GROUP_TODAY = { mr: "आज", hi: "आज", en: "Today" };
const GROUP_YDAY = { mr: "काल", hi: "कल", en: "Yesterday" };
const GROUP_30 = { mr: "मागील 30 दिवस", hi: "पिछले 30 दिन", en: "Previous 30 Days" };
const GROUP_OLDER = { mr: "जुने", hi: "पुराने", en: "Older" };
const NEW_CHAT_TITLE = { mr: "नवीन गप्पा", hi: "नई चैट", en: "New chat" };

const LANGS = ["mr", "hi", "en"];
const LANG_LABEL = { mr: "मराठी", hi: "हिंदी", en: "English" };

const ROW_LANGUAGE = { mr: "भाषा", hi: "भाषा", en: "Language" };
const ROW_VOICE = { mr: "व्हॉइस", hi: "वॉइस", en: "Voice" };
const ROW_THEME = { mr: "थीम", hi: "थीम", en: "Theme" };
const ROW_VERSION = { mr: "आवृत्ती", hi: "वर्शन", en: "Version" };
const HINT_OPEN = { mr: "कॉल उघडा", hi: "कॉल खोलें", en: "Open call" };
const HINT_LIGHT = { mr: "लाइट", hi: "लाइट", en: "Light" };
const CONFIRM_DELETE = { mr: "ही गप्पा हटवायची?", hi: "यह चैट हटाएं?", en: "Delete this chat?" };

// Right slide-in drawer opened by the header hamburger — Chats/Settings
// pill tabs, recency-grouped thread list with hover-delete, and a fixed
// "+ New Chat" footer. Matches the Pravasi Setu reference ThreadsDrawer.
export default function ThreadsDrawer({ open, onClose, threads, activeId, onPick, onNewChat, onDelete = deleteThread }) {
  const [tab, setTab] = useState("chats");
  const { language, setLanguage } = useLang();
  const navigate = useNavigate();
  if (!open) return null;

  const list = Object.values(threads || {});
  const groups = groupByRecency(list);

  return (
    <>
      <div onClick={onClose} className="fixed inset-0 bg-ink/50 backdrop-blur-[2px] z-40 animate-fade-in" />
      <aside className="fixed inset-y-0 right-0 z-50 w-full sm:w-[440px] bg-surface shadow-drawer animate-slide-in-right flex flex-col">
        <div className="px-4 pt-4 pb-2 flex-shrink-0">
          <div className="flex items-center bg-surface-2 rounded-full p-1">
            <TabButton
              active={tab === "chats"}
              onClick={() => setTab("chats")}
              icon={<MessageSquare size={14} />}
              label={t(TAB_CHATS, language)}
            />
            <TabButton
              active={tab === "settings"}
              onClick={() => setTab("settings")}
              icon={<SettingsIcon size={14} />}
              label={t(TAB_SETTINGS, language)}
            />
            <button
              onClick={onClose}
              className="ml-2 w-8 h-8 rounded-full hover:bg-white flex items-center justify-center text-muted flex-shrink-0"
              aria-label="Close"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pt-3 pb-24">
          {tab === "chats" && (
            <>
              {list.length === 0 && (
                <div className="text-center py-14 text-muted text-[13px]">{t(EMPTY, language)}</div>
              )}
              <ThreadGroup title={t(GROUP_TODAY, language)} threads={groups.today} activeId={activeId} onPick={onPick} onDelete={onDelete} language={language} />
              <ThreadGroup title={t(GROUP_YDAY, language)} threads={groups.yesterday} activeId={activeId} onPick={onPick} onDelete={onDelete} language={language} />
              <ThreadGroup title={t(GROUP_30, language)} threads={groups.prev30} activeId={activeId} onPick={onPick} onDelete={onDelete} language={language} />
              <ThreadGroup title={t(GROUP_OLDER, language)} threads={groups.older} activeId={activeId} onPick={onPick} onDelete={onDelete} language={language} />
            </>
          )}
          {tab === "settings" && (
            <div className="pt-4 space-y-1">
              <div className="border-b border-bdr-soft py-3">
                <div className="text-[14px] font-semibold text-ink mb-2">{t(ROW_LANGUAGE, language)}</div>
                <div className="flex items-center gap-2">
                  {LANGS.map((l) => (
                    <button
                      key={l}
                      onClick={() => setLanguage(l)}
                      className={`flex-1 h-9 rounded-xl text-[12.5px] font-bold border transition ${
                        l === language
                          ? "bg-primary text-white border-primary"
                          : "bg-white text-ink border-bdr hover:border-primary"
                      }`}
                    >
                      {LANG_LABEL[l]}
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={() => { onClose(); navigate("/voice"); }}
                className="w-full flex items-center gap-2 border-b border-bdr-soft py-3 text-left"
              >
                <Phone size={15} className="text-primary flex-shrink-0" />
                <div className="flex-1 text-[14px] font-semibold text-ink">{t(ROW_VOICE, language)}</div>
                <div className="text-[12px] text-primary font-bold">{t(HINT_OPEN, language)}</div>
                <ChevronRight size={15} className="text-muted" />
              </button>
              <SettingsRow label={t(ROW_THEME, language)} hint={t(HINT_LIGHT, language)} />
              <SettingsRow label={t(ROW_VERSION, language)} hint="0.1.0 · dev" />
            </div>
          )}
        </div>

        <div className="border-t border-bdr px-4 py-4 bg-surface flex-shrink-0">
          <button
            onClick={onNewChat}
            className="w-full h-12 rounded-full bg-primary hover:bg-primary-700 text-white text-[14.5px] font-extrabold flex items-center justify-center gap-2"
          >
            <Plus size={17} /> {t(NEW_CHAT, language).replace(/^\+\s*/, "")}
          </button>
        </div>
      </aside>
    </>
  );
}

function ThreadGroup({ title, threads, activeId, onPick, onDelete, language }) {
  if (!threads || threads.length === 0) return null;
  return (
    <div className="mb-4">
      <div className="text-[13px] font-extrabold text-ink mb-1.5">{title}</div>
      <div className="space-y-1">
        {threads.map((th) => (
          <div
            key={th.id}
            className={`group w-full flex items-center gap-2 px-2 py-2 rounded-lg transition ${
              th.id === activeId ? "bg-primary-50" : "hover:bg-surface-2"
            }`}
          >
            <button onClick={() => onPick(th.id)} className="flex-1 min-w-0 text-left">
              <div className="text-[13.5px] font-semibold text-ink truncate">{th.title || t(NEW_CHAT_TITLE, language)}</div>
            </button>
            <button
              onClick={() => {
                if (window.confirm(t(CONFIRM_DELETE, language))) onDelete(th.id);
              }}
              className="opacity-0 group-hover:opacity-100 w-7 h-7 rounded-full text-muted hover:text-red-600 flex items-center justify-center"
              aria-label="Delete"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 h-9 rounded-full flex items-center justify-center gap-1.5 text-[13px] font-bold transition ${
        active ? "bg-white text-primary shadow-card" : "text-muted hover:text-ink"
      }`}
    >
      {icon} {label}
    </button>
  );
}

function SettingsRow({ label, hint }) {
  return (
    <div className="flex items-center justify-between border-b border-bdr-soft py-3">
      <div className="text-[14px] font-semibold text-ink">{label}</div>
      <div className="text-[12px] text-muted">{hint}</div>
    </div>
  );
}
