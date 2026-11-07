import { configureApi, setAccessToken } from "@stem/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { createQueryClient } from "./lib/queryClient";
import { routes } from "./router";

export const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

/** Réponse SSE : un événement par statut, puis fermeture. */
export function sse(events: [string, unknown][]) {
  const text = events.map(([name, data]) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`).join("");
  return new Response(text, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

export type Route = (request: Request, body: unknown) => Response | undefined;

/** Remplace fetch par un faux serveur : `routes` reçoit chaque requête, renvoie une réponse ou undefined (404). */
export function mockApi(routesFn: Route) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      const isJson = request.headers.get("Content-Type")?.includes("application/json");
      const isForm = request.headers.get("Content-Type")?.includes("multipart/form-data");
      const text = isJson ? await request.clone().text() : "";
      const body = isForm
        ? await request.clone().formData()
        : text
          ? (JSON.parse(text) as unknown)
          : undefined;
      const path = new URL(request.url).pathname;
      calls.push({ method: request.method, path, body });
      return routesFn(request, body) ?? json(404, { detail: "Introuvable" });
    }),
  );
  return calls;
}

export function renderApp(url: string, { authenticated = false } = {}) {
  configureApi({ baseUrl: "http://api.test" });
  setAccessToken(authenticated ? "token" : null);
  const router = createMemoryRouter(routes, { initialEntries: [url] });
  render(
    <QueryClientProvider client={createQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}
