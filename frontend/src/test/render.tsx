import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";

import { routes } from "../routes";
import {
  reloadActingMember,
  SessionProvider,
  setActingMember,
  type ActingMember,
} from "../session";

interface RenderAppOptions {
  /** Who is using the app. Leave out to start signed out. */
  as?: ActingMember;
}

/** Render the whole app at `path`, the way a user would open it. */
export function renderApp(path: string, { as }: RenderAppOptions = {}) {
  setActingMember(as ?? null);
  reloadActingMember();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={queryClient}>
      <SessionProvider>
        <RouterProvider router={router} />
      </SessionProvider>
    </QueryClientProvider>,
  );
  return { user, router, queryClient };
}
