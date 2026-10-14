import { defineConfig, devices } from "@playwright/test";

/**
 * Acceptance tests: each one walks through a user story in a real browser against the real,
 * running app (frontend, backend and database), starting from the sample band.
 *
 * Run against Docker Compose (the default, http://localhost:8080) or, in a codespace while
 * `bash scripts/dev.sh` is running:  E2E_BASE_URL=http://127.0.0.1:5173 pnpm test:e2e
 */
export default defineConfig({
  testDir: "./e2e",
  // The stories share one database, so run them one at a time.
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
    ["junit", { outputFile: "reports/e2e-junit.xml" }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    // The sample gigs are in Eastern time; show them the way the band sees them.
    timezoneId: "America/New_York",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
