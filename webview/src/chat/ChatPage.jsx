import { useCallback, useEffect, useRef, useState } from "react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import { ErrorNote } from "../components/ui.jsx";
import { streamChat } from "../lib/api.js";
import { getContext } from "../lib/swiftchat.js";

const HINT = {
  mr: "वापरून पहा: 'नमस्कार' → भाषा निवडा → यात्रा निवडा → हवामान, दर, नोंदणी विचारा, किंवा आणीबाणी टाइप करा.",
  hi: "आज़माएं: 'नमस्ते' → भाषा चुनें → यात्रा चुनें → मौसम, दरें, पंजीकरण पूछें, या इमरजेंसी टाइप करें।",
  en: "Try: 'hello' → pick a language → pick a yatra → ask about weather, rates, register, or type an emergency.",
};

const PLACEHOLDER = {
  mr: "संदेश लिहा…",
  hi: "संदेश लिखें…",
  en: "Type a message…",
};

const SEND = { mr: "पाठवा", hi: "भेजें", en: "Send" };
const TYPING = { mr: "टाइप करत आहे…", hi: "टाइप कर रहा है…", en: "typing…" };

// Very small markdown-ish renderer: **bold**, [label](url), bare URLs,
// tel: links, and line breaks. Returns an array of React nodes.
function renderMarkdown(text) {
  if (!text) return null;
  const lines = String(text).split("\n");
  const nodes = [];
  lines.forEach((line, li) => {
    if (li > 0) nodes.push(<br key={`br-${li}`} />);
    nodes.push(...renderInline(line, `l${li}`));
  });
  return nodes;
}

function renderInline(line, keyPrefix) {
  // Combined regex: markdown links, bold, tel: links, bare urls.
  const re = /(\[([^\]]+)\]\((tel:[^)]+|https?:\/\/[^)]+)\))|(\*\*([^*]+)\*\*)|(tel:[+\d][\d-]*)|(https?:\/\/[^\s)]+)/g;
  const out = [];
  let last = 0;
  let m;
  let idx = 0;
  while ((m = re.exec(line))) {
    if (m.index > last) out.push(line.slice(last, m.index));
    if (m[1]) {
      // [label](url)
      out.push(
        <a key={`${keyPrefix}-${idx++}`} href={m[3]}>
          {m[2]}
        </a>
      );
    } else if (m[4]) {
      // **bold**
      out.push(<strong key={`${keyPrefix}-${idx++}`}>{m[5]}</strong>);
    } else if (m[6]) {
      // bare tel:
      out.push(
        <a key={`${keyPrefix}-${idx++}`} href={m[6]}>
          {m[6]}
        </a>
      );
    } else if (m[7]) {
      // bare url
      out.push(
        <a key={`${keyPrefix}-${idx++}`} href={m[7]}>
          {m[7]}
        </a>
      );
    }
    last = re.lastIndex;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}

export default function ChatPage() {
  const { language } = useLang();
  const conversationIdRef = useRef(null);
  if (conversationIdRef.current === null) {
    conversationIdRef.current = "web-" + Date.now();
  }
  const ctx = useRef(getContext()).current;

  const [messages, setMessages] = useState([]); // {id, role: 'user'|'bot', text}
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [waitingFirstDelta, setWaitingFirstDelta] = useState(false);
  const [error, setError] = useState(null);
  const listRef = useRef(null);
  const nextId = useRef(1);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || busy) return;
    setError(null);
    setDraft("");
    const userMsgId = nextId.current++;
    const botMsgId = nextId.current++;
    setMessages((prev) => [...prev, { id: userMsgId, role: "user", text }]);
    setBusy(true);
    setWaitingFirstDelta(true);
    setMessages((prev) => [...prev, { id: botMsgId, role: "bot", text: "" }]);

    try {
      await streamChat(
        { user_id: ctx.user_id, conversation_id: conversationIdRef.current, text },
        (chunk) => {
          setWaitingFirstDelta(false);
          setMessages((prev) =>
            prev.map((m) => (m.id === botMsgId ? { ...m, text: m.text + chunk } : m))
          );
        }
      );
    } catch (e) {
      setMessages((prev) => prev.filter((m) => m.id !== botMsgId));
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
      setWaitingFirstDelta(false);
    }
  }, [draft, busy, ctx.user_id]);

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat-page">
      <h1>{tr(strings, "chat", language)}</h1>
      <p className="chat-hint">{HINT[language] || HINT.en}</p>

      {error ? <ErrorNote>{error}</ErrorNote> : null}

      <div className="chat-list" ref={listRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">{HINT[language] || HINT.en}</div>
        ) : (
          messages.map((m) => (
            <div key={m.id} className={`chat-bubble-row ${m.role}`}>
              <div className={`chat-bubble ${m.role}`}>
                {m.role === "bot" && m.text === "" && waitingFirstDelta ? (
                  <span className="chat-typing">{TYPING[language] || TYPING.en}</span>
                ) : (
                  renderMarkdown(m.text)
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="chat-composer">
        <textarea
          rows={2}
          value={draft}
          placeholder={PLACEHOLDER[language] || PLACEHOLDER.en}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
        />
        <button type="button" onClick={send} disabled={busy || !draft.trim()}>
          {SEND[language] || SEND.en}
        </button>
      </div>
    </div>
  );
}
