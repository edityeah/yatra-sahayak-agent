// Resolve who/what context: SwiftChat BotExtension when embedded, else URL
// query (?user_id=&lang=&yatra=), else sensible dev defaults. This is what
// lets the SPA run both inside SwiftChat and as a plain test website.
export function getContext() {
  const q = new URLSearchParams(window.location.search);
  let user_id = q.get("user_id");
  let language = q.get("lang");
  let yatra = q.get("yatra");
  try {
    const be = window.BotExtension;
    if (be && typeof be.getPayload === "function") {
      const p = be.getPayload() || {};
      user_id = user_id || p.user_id;
    }
  } catch (e) { /* ignore — fall through to defaults */ }
  return {
    user_id: user_id || "web-tester",
    language: language || "mr",
    yatra: yatra || "pandharpur",
  };
}
