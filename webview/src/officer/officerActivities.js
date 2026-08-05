// Officer war-room modules — shown as the always-visible strip in the chat AND
// as the full grid at /officer/activities. Shared so both stay in sync.
export const OFFICER_ACTIVITIES = [
  { id: "sos", icon: "🆘", label: { mr: "SOS फीड", hi: "SOS फ़ीड", en: "SOS feed" },
    tagline: { mr: "आपत्कालीन नियंत्रण", hi: "आपातकालीन नियंत्रण", en: "Emergencies & escalation" },
    action: { type: "route", href: "/officer/sos" } },
  { id: "heatmap", icon: "🗺️", label: { mr: "गर्दी नकाशा", hi: "भीड़ मानचित्र", en: "Crowd map" },
    tagline: { mr: "थेट गर्दी व्यवस्थापन", hi: "लाइव भीड़ प्रबंधन", en: "Live occupancy & alerts" },
    action: { type: "route", href: "/officer/heatmap" } },
  { id: "alerts", icon: "📢", label: { mr: "सूचना पाठवा", hi: "अलर्ट भेजें", en: "Send alerts" },
    tagline: { mr: "यात्रेकरूंना सूचना", hi: "यात्रियों को सूचना", en: "Broadcast to pilgrims" },
    action: { type: "route", href: "/officer/alerts" } },
  { id: "grievances", icon: "📝", label: { mr: "तक्रारी", hi: "शिकायतें", en: "Grievances" },
    tagline: { mr: "तक्रार व्यवस्थापन", hi: "शिकायत प्रबंधन", en: "Complaints workflow" },
    action: { type: "route", href: "/officer/grievances" } },
  { id: "registry", icon: "🧾", label: { mr: "नोंदणी व हरवले", hi: "पंजीकरण व खोया", en: "Registry & L&F" },
    tagline: { mr: "यात्रेकरू व हरवले–सापडले", hi: "यात्री व खोया–पाया", en: "Pilgrims & lost-found" },
    action: { type: "route", href: "/officer/registry" } },
];
