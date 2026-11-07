// Suivi en direct par SSE (backend README §7) : client basé sur fetch pour envoyer le Bearer
// (EventSource ne le permet pas, et jamais de jeton dans l'URL).
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { authFetch, getBaseUrl } from "./client";

/** Le serveur ne parle pas SSE (proxy, ancienne API, objet disparu) : l'appelant bascule en polling. */
export class EventsUnavailable extends Error {
  constructor(
    readonly reason: "unsupported" | "gone" | "http",
    readonly status?: number,
  ) {
    super(`SSE indisponible : ${reason}`);
    this.name = "EventsUnavailable";
  }
}

class Reconnect extends Error {}

export type FollowOptions<T> = {
  /** Statuts qui terminent le flux (le serveur le ferme aussi). */
  terminal: readonly string[];
  /** Appelé pour chaque événement de statut : nom de l'événement = statut, `data` = la ressource. */
  onUpdate: (status: string, data: T) => void;
  signal?: AbortSignal;
  /** Délai avant reconnexion après une coupure (le serveur renvoie l'état courant). */
  retryMs?: number;
};

/**
 * Suit `path` jusqu'à un statut final. Se reconnecte sur coupure ou fermeture du serveur (durée bornée côté
 * API) ; rejette `EventsUnavailable` si le flux est impossible. Se termine sans erreur si `signal` est annulé.
 */
export function followEvents<T>(
  path: string,
  { terminal, onUpdate, signal, retryMs = 2000 }: FollowOptions<T>,
) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort);
  let done = false;

  return fetchEventSource(`${getBaseUrl()}${path}`, {
    signal: controller.signal,
    openWhenHidden: true, // `Accept: text/event-stream` est ajouté par la bibliothèque
    // authFetch : Bearer + refresh sur 401 ; la reconnexion reprend toujours le jeton courant.
    fetch: (input, init) => authFetch(new Request(input, init)),
    async onopen(response) {
      const type = response.headers.get("Content-Type") ?? "";
      if (response.ok && type.startsWith("text/event-stream")) return;
      if (response.status === 404) throw new EventsUnavailable("gone", 404);
      throw new EventsUnavailable(response.ok ? "unsupported" : "http", response.status);
    },
    onmessage(message) {
      if (!message.event || !message.data) return;
      if (message.event === "gone") throw new EventsUnavailable("gone");
      onUpdate(message.event, JSON.parse(message.data) as T);
      if (terminal.includes(message.event)) {
        done = true;
        controller.abort();
      }
    },
    onclose() {
      if (!done) throw new Reconnect();
    },
    onerror(error) {
      if (error instanceof EventsUnavailable) throw error;
      return retryMs; // coupure réseau ou fermeture du serveur : on se reconnecte
    },
  }).finally(() => signal?.removeEventListener("abort", abort));
}
