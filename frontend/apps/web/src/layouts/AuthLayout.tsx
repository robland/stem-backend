import { Outlet } from "react-router-dom";
import { APP_NAME } from "@/strings/fr";

export function AuthLayout() {
  return (
    <div className="flex min-h-dvh flex-col items-center px-4 py-8 sm:justify-center">
      <div className="w-full max-w-md">
        <p className="mb-6 text-center text-xl font-bold text-primary">{APP_NAME}</p>
        <main className="rounded-xl border border-border bg-surface p-5 sm:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
