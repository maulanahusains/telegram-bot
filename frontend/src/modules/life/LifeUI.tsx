import { useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { Icon, type IconName } from "./icons";

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="life-page-header"><div className="life-page-intro"><p className="eyebrow"><span className="live-dot" aria-hidden="true" />{eyebrow}</p><h1>{title}</h1>{description && <p className="intro-copy">{description}</p>}</div>{action}</div>;
}

export function SectionHeading({ eyebrow, title, action, count }: { eyebrow?: string; title: string; action?: ReactNode; count?: string }) {
  return <div className="section-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2></div>{action ?? (count && <span className="section-count">{count}</span>)}</div>;
}

export function StatusChip({ children, tone = "muted" }: { children: ReactNode; tone?: "green" | "warm" | "muted" | "danger" }) {
  return <span className={`status-chip status-${tone}`}>{tone === "green" && <Icon name="check" size={13} />}{children}</span>;
}

export function IconButton({ label, icon, onClick, disabled = false, className = "" }: { label: string; icon: IconName; onClick?: () => void; disabled?: boolean; className?: string }) {
  if (!onClick) return <span className={`icon-button ${className}`} role="img" aria-label={label} title={label}><Icon name={icon} /></span>;
  return <button className={`icon-button ${className}`} type="button" aria-label={label} title={label} onClick={onClick} disabled={disabled}><Icon name={icon} /></button>;
}

export function Toggle({ checked, label, onChange }: { checked: boolean; label: string; onChange?: () => void }) {
  return <label className="toggle-control"><input type="checkbox" checked={checked} aria-label={label} onChange={onChange} /><span /></label>;
}

export function LifeSelect({ name, value, options, placeholder = "Select an option", onChange, required = false, disabled = false }: { name?: string; value: string; options: Array<{ value: string; label: string }>; placeholder?: string; onChange: (value: string) => void; required?: boolean; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    if (!open) return;
    const closeOnOutsidePress = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsidePress);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePress);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return <div className={`life-select${open ? " is-open" : ""}${disabled ? " is-disabled" : ""}`} ref={rootRef}>
    <select className="life-select-proxy" name={name} value={value} onChange={(event) => onChange(event.target.value)} required={required} disabled={disabled} tabIndex={-1} aria-hidden="true">
      <option value="">{placeholder}</option>
      {options.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
    </select>
    <button className="life-select-trigger" type="button" aria-haspopup="listbox" aria-expanded={open} disabled={disabled} onClick={() => setOpen((current) => !current)}>
      <span className={selected ? "" : "is-placeholder"}>{selected?.label ?? placeholder}</span>
      <Icon name="chevron" size={16} />
    </button>
    {open && <div className="life-select-menu" role="listbox" aria-label={name ?? placeholder}>
      {options.map((option) => <button className={`life-select-option${option.value === value ? " is-selected" : ""}`} type="button" role="option" aria-selected={option.value === value} key={option.value} onClick={() => { onChange(option.value); setOpen(false); }}>{option.label}{option.value === value && <Icon name="check" size={14} />}</button>)}
    </div>}
  </div>;
}

export function CheckControl({ checked, label, onChange }: { checked: boolean; label: string; onChange?: () => void }) {
  return <label className="check-control"><input type="checkbox" checked={checked} aria-label={label} onChange={onChange} /><span><Icon name="check" size={14} /></span></label>;
}

export function BottomNav() {
  const items: Array<{ label: string; to: string; icon: IconName }> = [
    { label: "Today", to: "/app/today", icon: "home" },
    { label: "Planner", to: "/app/planner", icon: "calendar" },
    { label: "Grocery", to: "/app/grocery", icon: "cart" },
    { label: "Progress", to: "/app/progress", icon: "trend" },
    { label: "Settings", to: "/app/settings", icon: "settings" }
  ];
  return <nav className="bottom-nav" aria-label="Life navigation">{items.map((item) => <NavLink className={({ isActive }) => `nav-item${isActive ? " is-active" : ""}`} end to={item.to} key={item.to}><Icon name={item.icon} size={19} /><span>{item.label}</span></NavLink>)}</nav>;
}

export function ArrowLink({ children, to }: { children: ReactNode; to: string }) {
  return <NavLink className="text-link" to={to}>{children}<Icon name="arrow" size={15} /></NavLink>;
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const safeValue = Math.max(0, Math.min(100, value));
  return <div className="progress-track" aria-label={label} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(safeValue)}><span style={{ width: `${safeValue}%` }} /></div>;
}
