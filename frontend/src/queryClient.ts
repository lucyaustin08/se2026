import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./api/errors";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Retry network and server failures, but not answers like 403 or 404 that won't change.
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status < 500) && failureCount < 2,
      },
    },
  });
}
