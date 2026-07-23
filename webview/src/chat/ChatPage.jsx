import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";

// STUB — real chat UI (message list + composer over /messages SSE) lands in
// Task 3.
export default function ChatPage() {
  const { language } = useLang();
  return (
    <div>
      <h1>{tr(strings, "chat", language)}</h1>
      <p>coming in Plan 3</p>
    </div>
  );
}
