import { createContext, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowLeft, RefreshCw } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { getKey, setKey as persistKey } from "./officerApi.js";

const LANG_LABEL = { mr: "मरा", hi: "हिं", en: "EN" };

function LangSwitch() {
  const { language, setLanguage } = useLang();
  return (
    <div className="flex items-center gap-0.5 bg-surface-2 rounded-full p-0.5">
      {["mr", "hi", "en"].map((l) => (
        <button key={l} onClick={() => setLanguage(l)}
          className={`px-2 h-7 rounded-full text-[11px] font-bold transition ${
            language === l ? "bg-primary text-white" : "text-muted hover:text-ink"}`}>
          {LANG_LABEL[l]}
        </button>
      ))}
    </div>
  );
}

const KeyCtx = createContext("");
export const useOfficerKey = () => useContext(KeyCtx);

// Wraps every officer page: shows the admin-key unlock until a key is present,
// then renders a shared header (title, optional back, optional refresh) and the
// page content, with the key available via useOfficerKey().
export default function OfficerGate({ title, subtitle = "Officer dashboard", back = false, bare = false, onRefresh, children }) {
  const navigate = useNavigate();
  const [key, setK] = useState(() => getKey());

  // Auth comes from the URL, NOT a prompt: the officer bot opens its activities
  // with ?officerKey=<ADMIN_API_KEY> (SwiftChat BotExtension config), so officers
  // never see a login screen. We persist it and strip it from the address bar.
  useEffect(() => {
    if (key) return;
    const params = new URLSearchParams(window.location.search);
    const urlKey = (params.get("officerKey") || params.get("key") || "").trim();
    if (!urlKey) return;
    persistKey(urlKey);
    setK(urlKey);
    params.delete("officerKey");
    params.delete("key");
    const clean = window.location.pathname + (params.toString() ? `?${params}` : "") + window.location.hash;
    window.history.replaceState({}, "", clean);
  }, [key]);

  if (key && bare) {
    // Gate only — the child renders its own chrome (used by the chat landing).
    return <KeyCtx.Provider value={key}>{children}</KeyCtx.Provider>;
  }

  if (!key) {
    // No prompt (that UX can't exist in SwiftChat). PII stays protected — the
    // console only opens from the officer bot, which carries the key in the URL.
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center px-4 font-sans">
        <div className="w-full max-w-sm rounded-2xl border border-bdr bg-surface shadow-card p-6 text-center">
          <div className="w-12 h-12 rounded-full bg-primary-100 text-primary flex items-center justify-center mx-auto"><ShieldCheck size={22} /></div>
          <h1 className="mt-3 text-[17px] font-extrabold text-ink">Yatra Officer — Control Room</h1>
          <p className="mt-2 text-[13px] text-muted">Officer access only. Open the Control Room from your officer bot.</p>
        </div>
      </div>
    );
  }

  return (
    <KeyCtx.Provider value={key}>
      <div className="min-h-screen bg-surface-2 font-sans text-ink flex flex-col">
        <header className="h-14 px-3 sm:px-4 flex items-center gap-2 border-b border-bdr bg-surface sticky top-0 z-20 flex-shrink-0">
          {back ? (
            <button onClick={() => navigate("/officer")} className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted" aria-label="Back">
              <ArrowLeft size={18} />
            </button>
          ) : (
            <div className="w-9 h-9 rounded-full bg-primary-100 text-primary flex items-center justify-center"><ShieldCheck size={17} /></div>
          )}
          <div className="flex-1 min-w-0 leading-tight">
            <div className="text-[14.5px] font-extrabold truncate">{title}</div>
            <div className="text-[11px] text-muted truncate">{subtitle}</div>
          </div>
          <LangSwitch />
          {onRefresh ? (
            <button onClick={onRefresh} className="w-9 h-9 rounded-full hover:bg-surface-2 flex items-center justify-center text-muted" title="Refresh"><RefreshCw size={16} /></button>
          ) : null}
        </header>
        <div className="flex-1 min-h-0 flex flex-col">{children}</div>
      </div>
    </KeyCtx.Provider>
  );
}
