// Resolve a trilingual seed value ({mr,hi,en} or plain string) to a display
// string for the given language. Mirrors the server's seed.t() helper.
export function t(value, lang) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return value[lang] || value.en || Object.values(value)[0] || "";
}
