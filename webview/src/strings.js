// Small trilingual UI-label table for nav labels + page titles. Real page
// content (fetched from the agent) carries its own trilingual text; this
// file only covers chrome around it.

export const strings = {
  appName: { mr: "यात्रा सहाय्यक", hi: "यात्रा सहायक", en: "Yatra Sahayak" },
  chat: { mr: "गप्पा", hi: "चैट", en: "Chat" },
  pass: { mr: "यात्रा पास", hi: "यात्रा पास", en: "Yatra Pass" },
  wallet: { mr: "माझे यात्रा पास", hi: "मेरे यात्रा पास", en: "My Yatra Passes" },
  lostFound: { mr: "हरवले–सापडले", hi: "खोया–पाया", en: "Lost & Found" },
  grievance: { mr: "तक्रार", hi: "शिकायत", en: "Grievance" },
  walletEmpty: {
    mr: "अजून एकही पास नाही. चॅटमध्ये 'नोंदणी' करून पास काढा.",
    hi: "अभी कोई पास नहीं। चैट में 'पंजीकरण' करके पास बनाएं।",
    en: "No passes yet. Register in the chat to create one.",
  },
  downloadQr: { mr: "QR डाउनलोड करा", hi: "QR डाउनलोड करें", en: "Download QR" },
  shareWhatsapp: { mr: "WhatsApp वर पाठवा", hi: "WhatsApp पर भेजें", en: "Share on WhatsApp" },
  openPass: { mr: "पास उघडा", hi: "पास खोलें", en: "Open pass" },
  primaryTag: { mr: "मुख्य", hi: "मुख्य", en: "Primary" },
  shareText: {
    mr: "माझा यात्रा पास",
    hi: "मेरा यात्रा पास",
    en: "My Yatra Sahayak pass",
  },
  map: { mr: "मार्ग व मार्गदर्शक", hi: "मार्ग व गाइड", en: "Route & Guide" },
  logistics: { mr: "सुविधा", hi: "सुविधाएं", en: "Logistics" },
  transport: { mr: "वाहतूक नियोजन", hi: "परिवहन प्लानर", en: "Transport planner" },
  drills: { mr: "सराव", hi: "अभ्यास", en: "Drills" },
  advisories: { mr: "सूचना", hi: "सूचनाएं", en: "Advisories" },
  loading: { mr: "लोड होत आहे…", hi: "लोड हो रहा है…", en: "Loading…" },
  voice: { mr: "कॉल", hi: "कॉल", en: "Call" },
  call: { mr: "कॉल करा", hi: "कॉल करें", en: "Call" },
  hangUp: { mr: "कॉल बंद करा", hi: "कॉल समाप्त करें", en: "Hang up" },
  mute: { mr: "म्यूट", hi: "म्यूट", en: "Mute" },
  unmute: { mr: "अनम्यूट", hi: "अनम्यूट", en: "Unmute" },
  connecting: { mr: "जोडत आहे…", hi: "जोड़ा जा रहा है…", en: "Connecting…" },
  connected: { mr: "जोडले गेले", hi: "जुड़ गया", en: "Connected" },
  callEnded: { mr: "कॉल संपला", hi: "कॉल समाप्त हुई", en: "Call ended" },
  callAgain: { mr: "पुन्हा कॉल करा", hi: "फिर से कॉल करें", en: "Call again" },
  backToChat: { mr: "गप्पांकडे परत", hi: "चैट पर वापस", en: "Back to chat" },
  // Calling screen — white prefix + gold callee name, then subtitle.
  calling: { mr: "कॉल करत आहे", hi: "कॉल हो रहा है", en: "Calling" },
  calleeName: { mr: "यात्रा सहाय्यक", hi: "यात्रा सहायक", en: "Yatra Sahayak" },
  gettingReady: {
    mr: "बोलण्यासाठी तयार होत आहे",
    hi: "बात करने के लिए तैयार हो रहे हैं",
    en: "Getting ready to talk",
  },
  listening: { mr: "ऐकत आहे …", hi: "सुन रहे हैं …", en: "Listening …" },
  voiceUnavailable: {
    mr: "या डिप्लॉयमेंटवर व्हॉइस सुविधा सक्षम केलेली नाही — ॲडमिनला LiveKit की सेट करण्यास सांगा.",
    hi: "इस डिप्लॉयमेंट पर वॉइस सुविधा सक्षम नहीं है — एडमिन से LiveKit कीज़ सेट करने को कहें।",
    en: "Voice isn't enabled on this deployment yet — ask the admin to set the LiveKit keys.",
  },
  callHint: {
    mr: "कॉल करा दाबा आणि बोला — हवामानाबद्दल विचारा किंवा आणीबाणी असल्यास सांगा.",
    hi: "कॉल करें दबाएं और बोलें — मौसम के बारे में पूछें, या आपातकाल होने पर बताएं।",
    en: "Tap Call and speak — try asking about the weather, or say there's an emergency.",
  },
  callMicNote: {
    mr: "कॉलसाठी तुमच्या मायक्रोफोनचा वापर केला जाईल.",
    hi: "कॉल के लिए आपके माइक्रोफ़ोन का उपयोग किया जाएगा।",
    en: "Calls use your microphone.",
  },
  callError: {
    mr: "कॉल जोडता आला नाही. पुन्हा प्रयत्न करा.",
    hi: "कॉल कनेक्ट नहीं हो सकी। कृपया पुनः प्रयास करें।",
    en: "Couldn't connect the call. Please try again.",
  },
};

export function tr(table, key, lang) {
  const entry = table[key];
  if (!entry) return key;
  return entry[lang] || entry.en || Object.values(entry)[0] || key;
}
