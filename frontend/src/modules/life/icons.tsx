export type IconName =
  | "arrow"
  | "bell"
  | "calendar"
  | "cart"
  | "check"
  | "chevron"
  | "clock"
  | "close"
  | "edit"
  | "flame"
  | "home"
  | "leaf"
  | "logout"
  | "more"
  | "plus"
  | "scale"
  | "settings"
  | "shield"
  | "trend"
  | "user"
  | "warning"
  | "weight"
  | "workout";

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
}

export function Icon({ name, size = 20, className, strokeWidth = 1.8 }: IconProps) {
  const props = { className, fill: "none", height: size, stroke: "currentColor", strokeLinecap: "round" as const, strokeLinejoin: "round" as const, strokeWidth, viewBox: "0 0 24 24", width: size, "aria-hidden": true };
  switch (name) {
    case "arrow": return <svg {...props}><path d="m9 18 6-6-6-6" /></svg>;
    case "bell": return <svg {...props}><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 8.5h18C21 16 18 16 18 9Z" /><path d="M10 21h4" /></svg>;
    case "calendar": return <svg {...props}><path d="M5 4v16M19 4v16M5 7h14M5 17h14M8 4v3M16 4v3" /></svg>;
    case "cart": return <svg {...props}><path d="M4 8h16l-1 11H5L4 8ZM8 8a4 4 0 0 1 8 0M8 12v3M12 12v3M16 12v3" /></svg>;
    case "check": return <svg {...props}><path d="m5 12 4 4L19 6" /></svg>;
    case "chevron": return <svg {...props}><path d="m6 9 6 6 6-6" /></svg>;
    case "clock": return <svg {...props}><path d="M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>;
    case "close": return <svg {...props}><path d="m6 6 12 12M18 6 6 18" /></svg>;
    case "edit": return <svg {...props}><path d="m14 6 4 4M5 19l3.5-.8L19 7.7a2.1 2.1 0 0 0-3-3L5.5 15.2 5 19Z" /></svg>;
    case "flame": return <svg {...props}><path d="M12 3c2 3 5 5.4 5 9a5 5 0 0 1-10 0c0-2.3 1.2-4.2 3.2-6.4.3 2.2 1.3 3.1 2.3 3.7C12.8 7 12.2 5.6 12 3Z" /></svg>;
    case "home": return <svg {...props}><path d="m4 11 8-7 8 7v8a1 1 0 0 1-1 1h-4v-5H9v5H5a1 1 0 0 1-1-1v-8Z" /></svg>;
    case "leaf": return <svg {...props}><path d="M6.5 14.5c3.2-1.2 5.3-3.5 6.8-7.2 2.4 1.8 3.8 4.1 3.1 6.7-.7 2.7-3.3 4.4-6.1 4.4-1.7 0-3-.6-3.8-1.7" /><path d="M6.5 18.5c2.3-3.8 4.8-6.1 8.1-8.1" /></svg>;
    case "logout": return <svg {...props}><path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" /></svg>;
    case "more": return <svg {...props}><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></svg>;
    case "plus": return <svg {...props}><path d="M12 5v14M5 12h14" /></svg>;
    case "scale": return <svg {...props}><path d="M6 5h12M5 8h14M7 8l1.2 10.2a2 2 0 0 0 2 1.8h3.6a2 2 0 0 0 2-1.8L17 8" /><path d="M9 13h6M10 16h4" /></svg>;
    case "settings": return <svg {...props}><path d="M5 6h14M5 12h14M5 18h14M9 4v4M15 10v4M11 16v4" /></svg>;
    case "shield": return <svg {...props}><path d="M12 4 19 7v5c0 4.2-2.8 7.2-7 8-4.2-.8-7-3.8-7-8V7l7-3Z" /><path d="m9 12 2 2 4-4" /></svg>;
    case "trend": return <svg {...props}><path d="M4 18 9 12l4 3 7-9M4 20h16" /></svg>;
    case "user": return <svg {...props}><circle cx="12" cy="8" r="3" /><path d="M5 20a7 7 0 0 1 14 0" /></svg>;
    case "warning": return <svg {...props}><path d="M12 4 21 19H3L12 4Z" /><path d="M12 9v4M12 16h.01" /></svg>;
    case "weight": return <svg {...props}><path d="M5 4v16M19 4v16M5 7h14M5 17h14M8 4v3M16 4v3" /></svg>;
    case "workout": return <svg {...props}><path d="M4 9v6M7 7v10M17 7v10M20 9v6M7 12h10M3 10h4M17 10h4M3 14h4M17 14h4" /></svg>;
  }
}
