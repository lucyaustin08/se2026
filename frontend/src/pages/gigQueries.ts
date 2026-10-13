import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { unwrap } from "../api/errors";

export function gigQueryKey(gigId: number) {
  return ["gig", gigId] as const;
}

export function useGig(gigId: number) {
  return useQuery({
    queryKey: gigQueryKey(gigId),
    queryFn: () =>
      unwrap(api.GET("/api/v1/gigs/{gig_id}", { params: { path: { gig_id: gigId } } })),
  });
}

export function useMembers() {
  return useQuery({
    queryKey: ["members"],
    queryFn: () => unwrap(api.GET("/api/v1/members", { params: { query: { page_size: 100 } } })),
  });
}
