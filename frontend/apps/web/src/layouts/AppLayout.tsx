import { cn } from "@stem/ui";
import { Camera, House, Swords, TrendingUp, UserRound, type LucideIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { paths } from "@/paths";
import { APP_NAME, t } from "@/strings/fr";

type Tab = { to: string; label: string; icon: LucideIcon; primary?: boolean };

// Ordre du README (§2) : le Scanner, action principale, est au centre.
const TABS: Tab[] = [
  { to: paths.home, label: t.nav.home, icon: House },
  { to: paths.challenges, label: t.nav.challenges, icon: Swords },
  { to: paths.scan, label: t.nav.scan, icon: Camera, primary: true },
  { to: paths.progress, label: t.nav.progress, icon: TrendingUp },
  { to: paths.profile, label: t.nav.profile, icon: UserRound },
];

/**
 * Mobile : barre d'onglets en bas (pouce), Scanner central surélevé.
 * Écran large (≥ lg) : barre latérale, contenu centré.
 */
export function AppLayout() {
  return (
    <div className="min-h-dvh lg:flex">
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col gap-2 border-r border-border bg-surface p-4 lg:flex">
        <p className="mb-4 px-3 text-xl font-bold text-primary">{APP_NAME}</p>
        <nav aria-label={t.nav.main} className="flex flex-col gap-1">
          {TABS.map(({ to, label, icon: Icon, primary }) => (
            <NavLink
              key={to}
              to={to}
              end={to === paths.home}
              className={({ isActive }) =>
                cn(
                  "flex min-h-touch items-center gap-3 rounded-lg px-3 font-semibold transition-colors",
                  primary && !isActive && "bg-primary text-primary-fg hover:bg-primary/90",
                  !primary && !isActive && "text-muted hover:bg-surface-2 hover:text-fg",
                  isActive && "bg-primary-soft text-primary",
                )
              }
            >
              <Icon aria-hidden className="size-5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="mx-auto w-full max-w-3xl px-4 pb-28 pt-6 lg:pb-10 lg:pt-10">
        <Outlet />
      </main>

      <nav
        aria-label={t.nav.main}
        className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface/95 pb-safe-b backdrop-blur lg:hidden"
      >
        <ul className="mx-auto grid max-w-lg grid-cols-5">
          {TABS.map(({ to, label, icon: Icon, primary }) => (
            <li key={to} className="flex justify-center">
              <NavLink
                to={to}
                end={to === paths.home}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-14 w-full flex-col items-center justify-center gap-0.5 text-xs font-semibold",
                    isActive ? "text-primary" : "text-muted",
                  )
                }
              >
                {primary ? (
                  <span className="-mt-6 flex size-14 items-center justify-center rounded-full bg-primary text-primary-fg shadow-lg ring-4 ring-bg">
                    <Icon aria-hidden className="size-6" />
                  </span>
                ) : (
                  <Icon aria-hidden className="size-6" />
                )}
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
