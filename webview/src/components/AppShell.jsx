import { createContext, useContext, useMemo, useState, useCallback } from "react";
import { NavLink, useSearchParams } from "react-router-dom";
import { getContext } from "../lib/swiftchat.js";
import { strings, tr } from "../strings.js";

export const LangContext = createContext({ language: "mr", setLanguage: () => {} });

export function useLang() {
  return useContext(LangContext);
}

const LANGS = ["mr", "hi", "en"];

const NAV_ITEMS = [
  { to: "/", key: "chat", end: true },
  { to: "/yatri/pass", key: "pass" },
  { to: "/yatri/map", key: "map" },
  { to: "/yatri/logistics", key: "logistics" },
  { to: "/yatri/drills", key: "drills" },
  { to: "/yatri/advisories", key: "advisories" },
];

export function LangProvider({ children }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const ctx = useMemo(() => getContext(), []);
  const [language, setLanguageState] = useState(searchParams.get("lang") || ctx.language);

  const setLanguage = useCallback(
    (lang) => {
      setLanguageState(lang);
      const next = new URLSearchParams(searchParams);
      next.set("lang", lang);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const value = useMemo(
    () => ({ language, setLanguage, yatra: ctx.yatra, user_id: ctx.user_id }),
    [language, setLanguage, ctx.yatra, ctx.user_id]
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

function LanguageSwitcher() {
  const { language, setLanguage } = useLang();
  return (
    <div className="lang-switcher">
      {LANGS.map((l) => (
        <button
          key={l}
          type="button"
          className={`lang-btn${l === language ? " active" : ""}`}
          onClick={() => setLanguage(l)}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export default function AppShell({ children }) {
  const { language, yatra } = useLang();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-brand">
            <span className="app-brand-name">{tr(strings, "appName", language)}</span>
            {yatra ? <span className="app-brand-yatra">· {yatra}</span> : null}
          </div>
          <LanguageSwitcher />
        </div>
      </header>
      <nav className="app-nav">
        <div className="app-nav-inner">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={{ pathname: item.to, search: `?lang=${language}` }}
              end={item.end}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {tr(strings, item.key, language)}
            </NavLink>
          ))}
        </div>
      </nav>
      <main className="app-main">{children}</main>
    </div>
  );
}
