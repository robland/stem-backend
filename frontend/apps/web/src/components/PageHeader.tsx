import type { ReactNode } from "react";

export function PageHeader({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
      {subtitle ? <p className="text-muted mt-1">{subtitle}</p> : null}
    </header>
  );
}

/** Écran dont la maquette n'est pas encore validée (README frontend §2). */
export function ComingSoon({ children }: { children: ReactNode }) {
  return (
    <div className="border-border bg-surface text-muted rounded-xl border border-dashed p-6">{children}</div>
  );
}
