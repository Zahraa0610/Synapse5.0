import { useI18n } from "./context";
import { toneFor } from "./api";

export function Mark() {
  return (
    <svg width="36" height="36" viewBox="0 0 48 48" aria-hidden="true">
      <rect width="48" height="48" rx="14" fill="#1c4336" />
      <path d="M24 12c6 4 8 8 8 13a8 8 0 1 1-16 0c0-5 2-9 8-13z" fill="#f3f0e7" />
      <circle cx="24" cy="25" r="2.2" fill="#1c4336" />
    </svg>
  );
}

export function LangToggle() {
  const { lang, setLang } = useI18n();
  return (
    <div className="lang-toggle" role="group" aria-label="Language">
      <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")} type="button">EN</button>
      <button className={lang === "ar" ? "active" : ""} onClick={() => setLang("ar")} type="button">عربي</button>
    </div>
  );
}

export function Pill({ value, children }) {
  return <span className={`pill tone-${toneFor(value)}`}>{children || value}</span>;
}

export function Note({ children }) {
  return <p className="quiet-note">{children}</p>;
}

export function ErrorText({ children }) {
  if (!children) return null;
  return <div className="error">{children}</div>;
}

export function Field({ label, children }) {
  const { t } = useI18n();
  return (
    <label className="field">
      <span>{t(label)}</span>
      {children}
    </label>
  );
}

export function TextInput(props) {
  return <input {...props} />;
}

export function Select({ options, ...props }) {
  const { t } = useI18n();
  return (
    <select {...props}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>{t(option.label)}</option>
      ))}
    </select>
  );
}

export function Button({ children, soft, ghost, ...props }) {
  const { t } = useI18n();
  const className = ghost ? "btn-ghost" : soft ? "btn-soft" : "btn";
  return (
    <button className={`${className} ${props.className || ""}`} {...props}>
      {typeof children === "string" ? t(children) : children}
    </button>
  );
}

export function Empty({ children }) {
  return <p className="muted small">{children}</p>;
}

export function Bars({ value, max = 100, tone }) {
  const width = Math.max(0, Math.min(100, max ? (value / max) * 100 : 0));
  return (
    <div className={`bar ${tone || ""}`} aria-hidden="true">
      <span style={{ width: `${width}%` }} />
    </div>
  );
}

export function useT() {
  return useI18n().t;
}
