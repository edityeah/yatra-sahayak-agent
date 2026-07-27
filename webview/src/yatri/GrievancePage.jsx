import { useState } from "react";
import { Plus, CheckCircle2, ClipboardList } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiPost } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const L = {
  intro: { mr: "जास्त दर, सुविधा, स्वच्छता, सुरक्षा किंवा कर्मचाऱ्यांबद्दल तक्रार नोंदवा — ती थेट नियंत्रण कक्षाकडे जाते.",
           hi: "अधिक दाम, सुविधा, स्वच्छता, सुरक्षा या कर्मचारियों के बारे में शिकायत दर्ज करें — यह सीधे नियंत्रण कक्ष तक जाती है।",
           en: "Report overcharging, facilities, cleanliness, safety or staff conduct — it goes straight to the control room." },
  category: { mr: "प्रकार", hi: "श्रेणी", en: "Category" },
  desc: { mr: "काय झाले?", hi: "क्या हुआ?", en: "What happened?" },
  loc: { mr: "ठिकाण", hi: "स्थान", en: "Location" },
  yourName: { mr: "तुमचे नाव", hi: "आपका नाम", en: "Your name" },
  yourPhone: { mr: "तुमचा मोबाइल", hi: "आपका मोबाइल", en: "Your mobile" },
  submit: { mr: "तक्रार पाठवा", hi: "शिकायत भेजें", en: "Submit grievance" },
  submitting: { mr: "पाठवत आहे…", hi: "भेज रहे हैं…", en: "Submitting…" },
  filed: { mr: "तक्रार नोंदवली! संदर्भ", hi: "शिकायत दर्ज! संदर्भ", en: "Grievance filed! Reference" },
  need: { mr: "कृपया तपशील लिहा.", hi: "कृपया विवरण लिखें।", en: "Please describe the issue." },
};
const CATS = [
  { v: "overcharging", mr: "जास्त दर", hi: "अधिक दाम", en: "Overcharging" },
  { v: "facilities", mr: "सुविधा", hi: "सुविधाएं", en: "Facilities" },
  { v: "cleanliness", mr: "स्वच्छता", hi: "स्वच्छता", en: "Cleanliness" },
  { v: "safety", mr: "सुरक्षा", hi: "सुरक्षा", en: "Safety" },
  { v: "staff", mr: "कर्मचारी वर्तन", hi: "स्टाफ आचरण", en: "Staff conduct" },
  { v: "other", mr: "इतर", hi: "अन्य", en: "Other" },
];

export default function GrievancePage() {
  const { language, yatra } = useLang();
  const [f, setF] = useState({ category: "overcharging", description: "", location: "", reporter_name: "", reporter_phone: "" });
  const [busy, setBusy] = useState(false);
  const [filed, setFiled] = useState(null);
  const [err, setErr] = useState(null);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  const submit = async () => {
    if (!f.description.trim()) { setErr(t(L.need, language)); return; }
    setErr(null); setBusy(true);
    try { const { id } = await apiPost("/api/grievances", { ...f, yatra }); setFiled(id);
      setF({ category: "overcharging", description: "", location: "", reporter_name: "", reporter_phone: "" }); }
    catch (e) { setErr(e?.message || String(e)); }
    finally { setBusy(false); }
  };

  return (
    <PageShell title={tr(strings, "grievance", language)}>
      <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
        <div className="flex items-center gap-2 text-[14px] font-extrabold text-ink"><ClipboardList size={16} className="text-primary" /> {tr(strings, "grievance", language)}</div>
        <p className="text-[12.5px] text-muted leading-relaxed">{t(L.intro, language)}</p>
        {err ? <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 text-[13px] px-3 py-2">{err}</div> : null}

        <label className="block">
          <span className="text-[12.5px] font-bold text-ink">{t(L.category, language)}</span>
          <select value={f.category} onChange={set("category")} className="mt-1 w-full h-10 rounded-xl border border-bdr bg-surface px-3 text-[14px]">
            {CATS.map((c) => <option key={c.v} value={c.v}>{t(c, language)}</option>)}
          </select>
        </label>
        <Field k="description" label={L.desc} v={f} set={set} lang={language} area />
        <Field k="location" label={L.loc} v={f} set={set} lang={language} />
        <div className="grid grid-cols-2 gap-3">
          <Field k="reporter_name" label={L.yourName} v={f} set={set} lang={language} />
          <Field k="reporter_phone" label={L.yourPhone} v={f} set={set} lang={language} />
        </div>
        <button onClick={submit} disabled={busy} className="w-full h-11 rounded-full bg-primary text-white font-extrabold flex items-center justify-center gap-2 disabled:opacity-60 hover:bg-primary-700 transition">
          <Plus size={17} /> {busy ? t(L.submitting, language) : t(L.submit, language)}
        </button>
        {filed ? (
          <div className="rounded-xl border border-green-200 bg-green-50 text-green-800 text-[13.5px] px-3 py-2.5 flex items-center gap-2">
            <CheckCircle2 size={16} /> {t(L.filed, language)}: <span className="font-mono font-bold">{filed}</span>
          </div>
        ) : null}
      </div>
    </PageShell>
  );
}

function Field({ k, label, v, set, lang, area }) {
  return (
    <label className="block">
      <span className="text-[12.5px] font-bold text-ink">{t(label, lang)}</span>
      {area
        ? <textarea value={v[k]} onChange={set(k)} rows={3} className="mt-1 w-full rounded-xl border border-bdr bg-surface px-3 py-2 text-[14px] outline-none focus:border-primary" />
        : <input value={v[k]} onChange={set(k)} className="mt-1 w-full h-10 rounded-xl border border-bdr bg-surface px-3 text-[14px] outline-none focus:border-primary" />}
    </label>
  );
}
