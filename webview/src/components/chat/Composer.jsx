import { useEffect, useRef, useState } from "react";
import { Plus, Mic, Send, Square } from "lucide-react";
import { useLang } from "../AppShell.jsx";
import { t } from "../../lib/i18n.js";

const PLACEHOLDER = {
  mr: "संदेश पाठवण्यासाठी टॅप करा",
  hi: "संदेश भेजने के लिए टैप करें",
  en: "Tap to send a message",
};
const LISTENING = {
  mr: "ऐकत आहे… बोला",
  hi: "सुन रहा हूँ… बोलिए",
  en: "Listening… speak now",
};

// Browser speech-to-text. The mic DICTATES into the input (it is not a call —
// the voice CALL lives in Quick Activities → Voice Call). Recognition language
// follows the selected app language so Marathi/Hindi/English all transcribe.
const SpeechRecognition =
  typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
const RECOG_LANG = { mr: "mr-IN", hi: "hi-IN", en: "en-IN" };

// Composer strip at the bottom — [+] [ input ] [mic / send]. The + button
// opens the PersistentMenuDrawer (Camera/Gallery/Document/Quick Activities).
// The mic dictates; Send appears once there's text.
export default function Composer({ disabled, onSend, onPlus }) {
  const { language } = useLang();
  const [val, setVal] = useState("");
  const [listening, setListening] = useState(false);
  const inputRef = useRef(null);
  const recogRef = useRef(null);
  const baseRef = useRef("");   // text already in the box when dictation started

  // Stop any in-flight recognition on unmount.
  useEffect(() => () => { try { recogRef.current?.stop(); } catch { /* */ } }, []);

  function stopMic() {
    try { recogRef.current?.stop(); } catch { /* */ }
    setListening(false);
  }

  function submit() {
    const text = val.trim();
    if (!text || disabled) return;
    stopMic();
    onSend(text);
    setVal("");
    inputRef.current?.focus();
  }

  function toggleMic() {
    if (disabled || !SpeechRecognition) return;
    if (listening) { stopMic(); return; }

    const recog = new SpeechRecognition();
    recog.lang = RECOG_LANG[language] || "en-IN";
    recog.interimResults = true;   // update the box live as they speak
    recog.continuous = false;
    baseRef.current = val ? val.replace(/\s*$/, "") + " " : "";

    recog.onresult = (e) => {
      let transcript = "";
      for (let i = 0; i < e.results.length; i++) transcript += e.results[i][0].transcript;
      setVal(baseRef.current + transcript);
    };
    recog.onerror = () => setListening(false);
    recog.onend = () => { setListening(false); inputRef.current?.focus(); };

    recogRef.current = recog;
    setListening(true);
    try { recog.start(); } catch { setListening(false); }
  }

  const hasText = val.trim().length > 0;

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
        <div className={`flex-1 flex items-center rounded-full px-4 min-h-[42px] ${listening ? "bg-red-50 ring-1 ring-red-300" : "bg-surface-2"}`}>
          <input
            ref={inputRef}
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") { e.preventDefault(); submit(); }
            }}
            placeholder={listening ? t(LISTENING, language) : t(PLACEHOLDER, language)}
            disabled={disabled}
            className="flex-1 bg-transparent outline-none text-[14px] py-2 min-w-0"
          />
        </div>

        {listening ? (
          <button
            onClick={stopMic}
            className="w-10 h-10 rounded-full bg-red-500 text-white flex items-center justify-center flex-shrink-0 hover:bg-red-600 animate-pulse"
            aria-label="Stop dictation"
            title="Stop dictation"
          >
            <Square size={15} />
          </button>
        ) : hasText ? (
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
            onClick={toggleMic}
            disabled={disabled || !SpeechRecognition}
            className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center flex-shrink-0 hover:bg-primary-700 disabled:opacity-40"
            aria-label="Dictate a message"
            title={SpeechRecognition ? "Dictate a message" : "Voice input isn't supported in this browser"}
          >
            <Mic size={17} />
          </button>
        )}
      </div>
    </div>
  );
}
