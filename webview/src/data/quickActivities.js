// Yatra Quick Activities — shown as chips above the composer and as the
// full-page colored grid at /quick-activities. `action.type` is either
// "send" (feeds `text` into the chat as a user turn) or "route" (navigates
// to an in-app page).
export const QUICK_ACTIVITIES = [
  {
    id: "register",
    icon: "🪪",
    label: { mr: "नोंदणी / यात्रा पास", hi: "पंजीकरण / यात्रा पास", en: "Register / Yatra Pass" },
    tagline: { mr: "QR यात्रा पाससाठी नोंदणी करा", hi: "QR यात्रा पास के लिए पंजीकरण", en: "Register to get your QR pass" },
    action: { type: "send", text: "I want to register for the yatra" },
  },
  {
    id: "weather",
    icon: "🌦️",
    label: { mr: "हवामान", hi: "मौसम", en: "Weather" },
    tagline: { mr: "मार्गावरील हवामान अंदाज", hi: "मार्ग का मौसम", en: "Forecast on the route" },
    action: { type: "send", text: "what is the weather on the route today?" },
  },
  {
    id: "rates",
    icon: "🐎",
    label: { mr: "वाहतूक नियोजन", hi: "परिवहन प्लानर", en: "Transport planner" },
    tagline: { mr: "कुठून कुठे — खर्च काढा", hi: "कहाँ से कहाँ — खर्च जानें", en: "From → to → cost" },
    action: { type: "route", href: "/yatri/transport" },
  },
  {
    id: "helplines",
    icon: "☎️",
    label: { mr: "मदत क्रमांक", hi: "हेल्पलाइन", en: "Helplines" },
    tagline: { mr: "112 / 108 / नियंत्रण कक्ष", hi: "112 / 108 / नियंत्रण कक्ष", en: "112 / 108 / control room" },
    action: { type: "send", text: "give me the emergency helpline numbers" },
  },
  {
    id: "map",
    icon: "🧭",
    label: { mr: "मार्ग नकाशा", hi: "मार्ग मानचित्र", en: "Route Map" },
    tagline: { mr: "थांबे, घाट, सुविधा", hi: "पड़ाव, घाट, सुविधाएँ", en: "Halts, ghats, facilities" },
    action: { type: "route", href: "/yatri/map" },
  },
  {
    id: "advisories",
    icon: "📢",
    label: { mr: "सूचना", hi: "सूचनाएँ", en: "Advisories" },
    tagline: { mr: "जिल्हा प्रशासन सूचना", hi: "जिला सूचनाएँ", en: "District advisories" },
    action: { type: "route", href: "/yatri/advisories" },
  },
  {
    id: "drills",
    icon: "🆘",
    label: { mr: "सुरक्षा व सराव", hi: "सुरक्षा व अभ्यास", en: "Safety & Drills" },
    tagline: { mr: "आपत्कालीन तयारी", hi: "आपातकालीन तैयारी", en: "Emergency preparedness" },
    action: { type: "send", text: "what safety drills should I know?" },
  },
  {
    id: "lostfound",
    icon: "🧿",
    label: { mr: "हरवले–सापडले", hi: "खोया–पाया", en: "Lost & Found" },
    tagline: { mr: "व्यक्ती/वस्तू नोंदवा", hi: "व्यक्ति/वस्तु दर्ज करें", en: "Report a person or item" },
    action: { type: "route", href: "/yatri/lostfound" },
  },
  {
    id: "grievance",
    icon: "📝",
    label: { mr: "तक्रार", hi: "शिकायत", en: "Grievance" },
    tagline: { mr: "तक्रार नोंदवा", hi: "शिकायत दर्ज करें", en: "File a complaint" },
    action: { type: "route", href: "/yatri/grievance" },
  },
  {
    id: "call",
    icon: "📞",
    label: { mr: "व्हॉइस कॉल", hi: "वॉइस कॉल", en: "Voice Call" },
    tagline: { mr: "Setu शी बोला", hi: "Setu से बात करें", en: "Talk to Setu" },
    action: { type: "route", href: "/voice" },
  },
];
