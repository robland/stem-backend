import { Outlet } from "react-router-dom";

/** Parcours : plein écran sans onglets, pour rester concentré (maquettes 5 à 7). */
export function FocusLayout() {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-2xl flex-col">
      <Outlet />
    </div>
  );
}
