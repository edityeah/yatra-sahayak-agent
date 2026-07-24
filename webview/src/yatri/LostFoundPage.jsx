import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserRound, Package, MessageCircle, CheckCircle2, Plus } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet, apiPost } from "../lib/api.js";
import { t } from "../lib/i18n.js";

const L = {
  title: { mr: "हरवले–सापडले", hi: "खोया–पाया", en: "Lost & Found" },
  report: { mr: "नोंदवा", hi: "दर्ज करें", en: "Report" },
  board: { mr: "नोंदी", hi: "सूची", en: "Open reports" },
  person: { mr: "व्यक्ती", hi: "व्यक्ति", en: "Person" },
  item: { mr: "वस्तू", hi: "वस्तु", en: "Item" },
  name: { mr: "नाव", hi: "नाम", en: "Name" },
  desc: { mr: "वर्णन (कपडे, ओळख खुणा…)", hi: "विवरण (कपड़े, पहचान…)", en: "Description (clothing, marks…)" },
  lastSeen: { mr: "शेवटचे कुठे दिसले?", hi: "आख़िरी बार कहाँ देखा?", en: "Last seen where?" },
  yourName: { mr: "तुमचे नाव", hi: "आपका नाम", en: "Your name" },
  yourPhone: { mr: "तुमचा मोबाइल", hi: "आपका मोबाइल", en: "Your mobile" },
  yatraId: { mr: "यात्रा आयडी (असल्यास)", hi: "यात्रा आईडी (यदि हो)", en: "Yatra ID (if any)" },
  submit: { mr: "नोंद सबमिट करा", hi: "रिपोर्ट सबमिट करें", en: "Submit report" },
  submitting: { mr: "सबमिट होत आहे…", hi: "सबमिट हो रहा है…", en: "Submitting…" },
  filed: { mr: "नोंद झाली! संदर्भ", hi: "दर्ज हुई! संदर्भ", en: "Filed! Reference" },
  personNote: { mr: "व्यक्ती हरवल्यास नियंत्रण कक्षाला तात्काळ सूचना जाते व SOS नोंदतो.",
                hi: "व्यक्ति खोने पर नियंत्रण कक्ष को तुरंत सूचना जाती है व SOS दर्ज होता है।",
                en: "Reporting a person alerts the control room and raises an SOS immediately." },
  empty: { mr: "अजून कोणतीही नोंद नाही.", hi: "अभी कोई रिपोर्ट नहीं।", en: "No open reports yet." },
  reunited: { mr: "सापडले म्हणून खुणा करा", hi: "मिल गया चिह्नित करें", en: "Mark reunited" },
  resolved: { mr: "सापडले ✓", hi: "मिल गया ✓", en: "Reunited ✓" },
  ask: { mr: "चॅटमध्ये विचारा", hi: "चैट में पूछें", en: "Ask in chat" },
  required: { mr: "नाव व वर्णन आवश्यक.", hi: "नाम व विवरण आवश्यक।", en: "Name and description are required." },
};

export default function LostFoundPage() {
  const { language, yatra } = useLang();
  const navigate = useNavigate();
  const [tab, setTab] = useState("report");
  const [kind, setKind] = useState("person");
  const [form, setForm] = useState({ name: "", description: "", last_seen: "", reporter_name: "", reporter_phone: "", yatra_id: "" });
  const [busy, setBusy] = useState(false);
  const [filedId, setFiledId] = useState(null);
  const [err, setErr] = useState(null);
  const [reports, setReports] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const loadBoard = useCallback(() => {
    apiGet(`/api/lostfound?yatra=${yatra}`)
      .then((rows) => setReports(rows || []))
      .catch((e) => setErr(e?.message || String(e)));
  }, [yatra]);

  useEffect(() => { if (tab === "board") loadBoard(); }, [tab, loadBoard]);

  const submit = async () => {
    if (!form.name.trim() || !form.description.trim()) { setErr(t(L.required, language)); return; }
    setErr(null); setBusy(true);
    try {
      const { id } = await apiPost("/api/lostfound", { ...form, kind, yatra });
      setFiledId(id);
      setForm({ name: "", description: "", last_seen: "", reporter_name: "", reporter_phone: "", yatra_id: "" });
    } catch (e) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const resolve = async (id) => {
    try { await apiPost(`/api/lostfound/${id}/status`, { status: "reunited" }); loadBoard(); }
    catch (e) { setErr(e?.message || String(e)); }
  };

  const askInChat = (q) => navigate(`/?q=${encodeURIComponent(q)}`);
  const Field = ({ k, label, ph }) => (
    <label className="block">
      <span className="text-[12.5px] font-bold text-ink">{t(label, language)}</span>
      <input value={form[k]} onChange={set(k)} placeholder={ph || ""}
        className="mt-1 w-full h-10 rounded-xl border border-bdr bg-surface px-3 text-[14px] text-ink focus:border-primary outline-none" />
    </label>
  );

  return (
    <PageShell title={tr(strings, "lostFound", language) || t(L.title, language)}>
      {/* tabs */}
      <div className="flex items-center bg-surface-2 rounded-full p-1 mb-3 max-w-xs">
        {["report", "board"].map((tb) => (
          <button key={tb} onClick={() => setTab(tb)}
            className={`flex-1 h-9 rounded-full text-[13px] font-bold transition ${tab === tb ? "bg-white text-primary shadow-card" : "text-muted"}`}>
            {t(tb === "report" ? L.report : L.board, language)}
          </button>
        ))}
      </div>

      {err ? <div className="mb-3 rounded-xl border border-red-200 bg-red-50 text-red-700 text-[13px] px-3 py-2">{err}</div> : null}

      {tab === "report" ? (
        <div className="rounded-2xl border border-bdr bg-surface shadow-card p-4 space-y-3">
          {/* kind toggle */}
          <div className="flex gap-2">
            {[["person", L.person, UserRound], ["item", L.item, Package]].map(([k, lbl, Icon]) => (
              <button key={k} onClick={() => setKind(k)}
                className={`flex-1 h-11 rounded-xl border text-[13.5px] font-bold flex items-center justify-center gap-2 transition ${
                  kind === k ? "bg-primary text-white border-primary" : "bg-surface text-ink border-bdr"}`}>
                <Icon size={16} /> {t(lbl, language)}
              </button>
            ))}
          </div>
          {kind === "person" ? (
            <p className="text-[12px] text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">{t(L.personNote, language)}</p>
          ) : null}

          <Field k="name" label={L.name} />
          <Field k="description" label={L.desc} />
          <Field k="last_seen" label={L.lastSeen} />
          <div className="grid grid-cols-2 gap-3">
            <Field k="reporter_name" label={L.yourName} />
            <Field k="reporter_phone" label={L.yourPhone} />
          </div>
          <Field k="yatra_id" label={L.yatraId} />

          <button onClick={submit} disabled={busy}
            className="w-full h-11 rounded-full bg-primary text-white font-extrabold flex items-center justify-center gap-2 disabled:opacity-60 hover:bg-primary-700 transition">
            <Plus size={17} /> {busy ? t(L.submitting, language) : t(L.submit, language)}
          </button>

          {filedId ? (
            <div className="rounded-xl border border-green-200 bg-green-50 text-green-800 text-[13.5px] px-3 py-2.5 flex items-center gap-2">
              <CheckCircle2 size={16} /> {t(L.filed, language)}: <span className="font-mono font-bold">{filedId}</span>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="space-y-3">
          {reports === null ? <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div> : null}
          {reports && reports.length === 0 ? <div className="text-center py-12 text-muted text-[13.5px]">{t(L.empty, language)}</div> : null}
          {(reports || []).map((r) => (
            <div key={r.id} className="rounded-2xl border border-bdr bg-surface shadow-card p-4">
              <div className="flex items-start gap-2">
                <span className={`mt-0.5 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${r.kind === "person" ? "bg-primary-100 text-primary" : "bg-amber-100 text-amber-700"}`}>
                  {r.kind === "person" ? <UserRound size={16} /> : <Package size={16} />}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14.5px] font-extrabold text-ink">{r.name || "—"}</span>
                    {r.status === "reunited" ? (
                      <span className="text-[11px] font-bold text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">{t(L.resolved, language)}</span>
                    ) : null}
                  </div>
                  <div className="text-[11.5px] font-bold text-muted uppercase tracking-wide">
                    {t(r.kind === "person" ? L.person : L.item, language)}{r.id ? ` · ${r.id}` : ""}
                  </div>
                  {r.description ? <p className="mt-1 text-[13px] text-ink leading-relaxed">{r.description}</p> : null}
                  {r.last_seen ? <p className="text-[12.5px] text-muted">📍 {r.last_seen}</p> : null}
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {r.status !== "reunited" ? (
                      <button onClick={() => resolve(r.id)}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-green-600 text-white text-[12px] font-bold px-2.5 h-8 hover:bg-green-700 transition">
                        <CheckCircle2 size={13} /> {t(L.reunited, language)}
                      </button>
                    ) : null}
                    <button onClick={() => askInChat(`${t(L.title, language)}: ${r.name || r.id}`)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-bdr bg-surface-2 text-ink text-[12px] font-bold px-2.5 h-8 hover:border-primary transition">
                      <MessageCircle size={13} /> {t(L.ask, language)}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </PageShell>
  );
}
