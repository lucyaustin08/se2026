import createClient, { type Middleware } from "openapi-fetch";

import { getActingMember } from "../session";
import type { paths } from "./schema";

export const ACTING_MEMBER_HEADER = "X-Acting-Member-Id";

const sendActingMember: Middleware = {
  onRequest({ request }) {
    const member = getActingMember();
    if (member) request.headers.set(ACTING_MEMBER_HEADER, String(member.id));
    return request;
  },
};

/** Typed API client. Paths, parameters and bodies are checked against the backend schema. */
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  // Look up fetch on every call, so tools that replace it after startup (MSW) are used.
  fetch: (request) => globalThis.fetch(request),
});
api.use(sendActingMember);
