import { restoreSession, useSession } from "@stem/api-client";
import { Spinner } from "@stem/ui";
import { useEffect, type ReactNode } from "react";
import { APP_NAME, t } from "@/strings/fr";

let restoring: Promise<boolean> | null = null;

/** Au chargement, tente de restaurer la session depuis le cookie de refresh avant d'afficher les routes. */
export function SessionGate({ children }: { children: ReactNode }) {
  const status = useSession();

  useEffect(() => {
    if (status === "unknown") restoring ??= restoreSession();
  }, [status]);

  if (status === "unknown") {
    return (
      <div className="text-muted flex min-h-dvh flex-col items-center justify-center gap-4">
        <span className="text-primary text-xl font-bold">{APP_NAME}</span>
        <Spinner label={t.common.loading} />
      </div>
    );
  }
  return children;
}
