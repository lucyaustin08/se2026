/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development, send API calls to the backend running on the host.
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    // Fixed time zone, so tests that convert local times to UTC give the same answer everywhere.
    env: { TZ: "America/New_York" },
    setupFiles: ["./test_setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/**/*.test.{ts,tsx}", "src/**/*.d.ts", "src/test/**"],
      reporter: ["text", "html"],
      thresholds: { lines: 80 },
    },
  },
});
