// Shared helpers for distributing a yatra pass (used by PassPage + WalletPage).

// Absolute URL that renders a single pass — this is what a QR encodes and what
// gets shared, so opening/scanning it lands on the pass (in `lang` if given).
export function passUrl(yatraId, lang) {
  const q = lang ? `&lang=${lang}` : "";
  return `${window.location.origin}/yatri/pass?id=${yatraId}${q}`;
}

// Trigger a browser download of a QR data-URL (PNG) as a file.
export function downloadQr(dataUrl, yatraId) {
  if (!dataUrl) return;
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = `yatra-pass-${yatraId}.png`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// wa.me deep link that pre-fills the share message + the pass link.
export function whatsappUrl(yatraId, text, lang) {
  return `https://wa.me/?text=${encodeURIComponent(`${text}: ${passUrl(yatraId, lang)}`)}`;
}
