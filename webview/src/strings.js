// Small trilingual UI-label table for nav labels + page titles. Real page
// content (fetched from the agent) carries its own trilingual text; this
// file only covers chrome around it.

export const strings = {
  appName: { mr: "यात्रा सहाय्यक", hi: "यात्रा सहायक", en: "Yatra Sahayak" },
  chat: { mr: "गप्पा", hi: "चैट", en: "Chat" },
  pass: { mr: "यात्रा पास", hi: "यात्रा पास", en: "Yatra Pass" },
  map: { mr: "मार्ग नकाशा", hi: "मार्ग मानचित्र", en: "Route Map" },
  logistics: { mr: "सुविधा", hi: "सुविधाएं", en: "Logistics" },
  drills: { mr: "सराव", hi: "अभ्यास", en: "Drills" },
  advisories: { mr: "सूचना", hi: "सूचनाएं", en: "Advisories" },
  loading: { mr: "लोड होत आहे…", hi: "लोड हो रहा है…", en: "Loading…" },
};

export function tr(table, key, lang) {
  const entry = table[key];
  if (!entry) return key;
  return entry[lang] || entry.en || Object.values(entry)[0] || key;
}
