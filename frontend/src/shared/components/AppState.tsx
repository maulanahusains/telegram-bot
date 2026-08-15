import type { ReactNode } from "react";

interface AppStateProps {
  title: string;
  children: ReactNode;
}

export function AppState({ title, children }: AppStateProps) {
  return (
    <main className="state-page">
      <section className="state-card" aria-live="polite">
        <p className="eyebrow">Telegram Platform</p>
        <h1>{title}</h1>
        <div className="state-copy">{children}</div>
      </section>
    </main>
  );
}
