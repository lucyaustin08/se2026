import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { setActingMember } from "./src/session";
import { resetMockData } from "./src/test/handlers";
import { server } from "./src/test/server";

// Any request without a handler fails the test, so no test silently hits the network.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

afterEach(() => {
  cleanup();
  server.resetHandlers();
  resetMockData();
  setActingMember(null);
});

afterAll(() => server.close());
