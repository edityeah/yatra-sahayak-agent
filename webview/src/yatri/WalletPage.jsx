import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";
import { Download, Share2, ExternalLink } from "lucide-react";
import { useLang } from "../components/AppShell.jsx";
import { strings, tr } from "../strings.js";
import PageShell from "../components/PageShell.jsx";
import { apiGet } from "../lib/api.js";
import { t } from "../lib/i18n.js";
import { YATRA_NAMES } from "../data/yatraNames.js";
import { getContext } from "../lib/swiftchat.js";
import { downloadQr, whatsappUrl, passUrl } from "../lib/passShare.js";

// The yatri wallet — every pass registered from this device/account, each with
// its own QR, Download and WhatsApp share (the DigiYatra-style pass list).
export default function WalletPage() {
  const { language } = useLang();
  const ctx = getContext();
  const [passes, setPasses] = useState(null);
  const [qrs, setQrs] = useState({}); // yatra_id -> data URL
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    apiGet(`/api/passes?user_id=${encodeURIComponent(ctx.user_id)}`)
      .then(async (rows) => {
        if (cancelled) return;
        setPasses(rows || []);
        const entries = await Promise.all(
          (rows || []).map(async (r) => [
            r.yatra_id,
            await QRCode.toDataURL(passUrl(r.yatra_id), { width: 240, margin: 1 }),
          ])
        );
        if (!cancelled) setQrs(Object.fromEntries(entries));
      })
      .catch((e) => !cancelled && setError(e?.message || String(e)));
    return () => {
      cancelled = true;
    };
  }, [ctx.user_id]);

  return (
    <PageShell title={tr(strings, "wallet", language)}>
      {error ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 text-red-700 text-[13.5px] px-4 py-3">{error}</div>
      ) : null}

      {passes && passes.length === 0 && !error ? (
        <div className="text-center py-14 text-muted text-[13.5px]">{tr(strings, "walletEmpty", language)}</div>
      ) : null}

      {passes === null && !error ? (
        <div className="text-[13.5px] text-muted px-1 py-3">{tr(strings, "loading", language)}</div>
      ) : null}

      <div className="space-y-3">
        {(passes || []).map((p) => (
          <div key={p.yatra_id} className="rounded-2xl border border-bdr bg-surface shadow-card overflow-hidden">
            <div className="bg-primary text-white px-4 py-2 flex items-center justify-between gap-2">
              <div className="text-[12px] font-bold tracking-wide uppercase truncate">
                {YATRA_NAMES[p.yatra] ? t(YATRA_NAMES[p.yatra], language) : p.yatra}
              </div>
              {p.is_primary ? (
                <span className="text-[10.5px] font-bold bg-white/20 rounded-full px-2 py-0.5">
                  {tr(strings, "primaryTag", language)}
                </span>
              ) : null}
            </div>
            <div className="p-4 flex gap-4 items-center">
              <div className="w-[96px] h-[96px] flex-shrink-0 rounded-lg border border-bdr bg-white flex items-center justify-center overflow-hidden">
                {qrs[p.yatra_id] ? <img src={qrs[p.yatra_id]} alt="QR" width={96} height={96} /> : null}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[15px] font-extrabold text-ink truncate">{p.name}</div>
                {p.age ? <div className="text-[12px] text-muted">{p.age}</div> : null}
                <div className="text-[11.5px] font-mono text-muted break-all mt-0.5">{p.yatra_id}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Link
                    to={`/yatri/pass?id=${p.yatra_id}`}
                    className="h-8 px-2.5 rounded-lg border border-bdr bg-surface-2 text-ink text-[11.5px] font-bold flex items-center gap-1 hover:border-primary transition"
                  >
                    <ExternalLink size={13} /> {tr(strings, "openPass", language)}
                  </Link>
                  <button
                    type="button"
                    onClick={() => downloadQr(qrs[p.yatra_id], p.yatra_id)}
                    className="h-8 px-2.5 rounded-lg border border-bdr bg-surface-2 text-ink text-[11.5px] font-bold flex items-center gap-1 hover:border-primary transition"
                  >
                    <Download size={13} /> {tr(strings, "downloadQr", language)}
                  </button>
                  <a
                    href={whatsappUrl(p.yatra_id, `${tr(strings, "shareText", language)} — ${p.name}`)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="h-8 px-2.5 rounded-lg bg-[#25D366] text-white text-[11.5px] font-bold flex items-center gap-1 hover:opacity-90 transition"
                  >
                    <Share2 size={13} /> WhatsApp
                  </a>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </PageShell>
  );
}
