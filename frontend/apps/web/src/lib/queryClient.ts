import { isApiError } from "@stem/api-client";
import { QueryClient } from "@tanstack/react-query";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Réseau instable : on réessaie les coupures, pas les erreurs du serveur 4xx.
        retry: (count, error) => count < 2 && !(isApiError(error) && error.status < 500),
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}
