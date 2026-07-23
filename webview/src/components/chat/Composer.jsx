import { useRef, useState } from "react";
import { Plus, Mic, Send } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const PLACEHOLDER = {
  mr: "संदेश पाठवण्यासाठी टॅप करा",
  hi: "संदेश भेजने के लिए टैप करें",
  en: "Tap to send a message",
};

// Composer strip at the bottom — [+] [ input ] [mic / send]. The + button
// opens the QuickActivitiesSheet. Mic and Send swap based on whether
// there's text in the input.
export default function Composer({ disabled, onSend, onPlus }) {
  const { language } = useLang();
  const navigate = useNavigate();
  const [val, setVal] = useState("");
  const inputRef = useRef(null);

  function submit() {
    const text = val.trim();
    if (!text || disabled) return;
    onSend(text);
    setVal("");
    inputRef.current?.focus();
  }

  return (
    <div className="flex-shrink-0 border-t border-bdr bg-surface">
      <div className="max-w-3xl w-full mx-auto px-3 py-2.5 flex items-center gap-2">
        <button
          onClick={onPlus}
          className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 hover:bg-primary-700"
          aria-label="Quick activities"
          title="Quick activities"
        >
          <Plus size={17} />
        </button>
        <div className="flex-1 flex items-center bg-surface-2 rounded-full px-4 min-h-[42px]">
          <input
            ref={inputRef}
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={t(PLACEHOLDER, language)}
            disabled={disabled}
            className="flex-1 bg-transparent outline-none text-[14px] py-2 min-w-0"
          />
        </div>
        {val.trim() ? (
          <button
            onClick={submit}
            disabled={disabled}
            className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 hover:bg-primary-700 disabled:opacity-40"
            aria-label="Send"
          >
            <Send size={17} />
          </button>
        ) : (
          <button
            onClick={() => navigate("/voice")}
            className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 hover:bg-primary-700"
            aria-label="Voice call"
            title="Voice call"
          >
            <Mic size={17} />
          </button>
        )}
      </div>
    </div>
  );
}
