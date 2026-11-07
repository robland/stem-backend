import { useSession } from "@stem/api-client";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { paths } from "@/paths";

export function RequireAuth() {
  const status = useSession();
  const location = useLocation();
  if (status !== "authenticated")
    return <Navigate to={paths.login} replace state={{ from: location.pathname }} />;
  return <Outlet />;
}

/** Pages de connexion / inscription : un élève connecté est renvoyé là où il allait. */
export function RequireAnonymous() {
  const status = useSession();
  const location = useLocation();
  if (status === "authenticated") {
    const from = (location.state as { from?: string } | null)?.from;
    return <Navigate to={from ?? paths.home} replace />;
  }
  return <Outlet />;
}
