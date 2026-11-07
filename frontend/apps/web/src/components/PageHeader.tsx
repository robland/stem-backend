import type { ReactNode } from "react";

export function PageHeader({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
      {subtitle ? <p className="mt-1 text-muted">{subtitle}</p> : null}
    </header>
  );
}

/** Écran dont la maquette n'est pas encore validée (README frontend §2). */
export function ComingSoon({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-border bg-surface p-6 text-muted">{children}</div>;
}
