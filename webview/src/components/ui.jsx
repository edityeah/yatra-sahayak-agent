// Small shared UI primitives — plain CSS classes (see src/styles.css), no
// heavy component library.

export function Card({ children, className = "", ...rest }) {
  return (
    <div className={`card ${className}`.trim()} {...rest}>
      {children}
    </div>
  );
}

const PILL_TONES = {
  default: "pill",
  ok: "pill pill-ok",
  warn: "pill pill-warn",
  danger: "pill pill-danger",
};

export function Pill({ children, tone = "default" }) {
  return <span className={PILL_TONES[tone] || PILL_TONES.default}>{children}</span>;
}

export const Badge = Pill;

export function Loading({ text = "Loading…" }) {
  return <div className="loading">{text}</div>;
}

export function ErrorNote({ children }) {
  return <div className="error-note">{children}</div>;
}
