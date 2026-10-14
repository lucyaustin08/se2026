import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatMoney,
  formatTime,
  localInputsToIso,
  toDateInputValue,
  toTimeInputValue,
} from "./format";

// Tests run in America/New_York (see vite.config.ts).
describe("time conversions", () => {
  it("turns a local date and time into UTC for the API", () => {
    expect(localInputsToIso("2026-10-18", "20:00")).toBe("2026-10-19T00:00:00.000Z");
  });

  it("uses standard time after daylight saving ends", () => {
    expect(localInputsToIso("2026-11-02", "20:00")).toBe("2026-11-03T01:00:00.000Z");
  });

  it("shows a UTC time from the API in local time", () => {
    expect(toDateInputValue("2026-10-19T00:00:00Z")).toBe("2026-10-18");
    expect(toTimeInputValue("2026-10-19T00:00:00Z")).toBe("20:00");
    expect(formatDate("2026-10-19T00:00:00Z")).toBe("Sun, Oct 18, 2026");
    expect(formatTime("2026-10-19T00:00:00Z")).toBe("8:00 PM");
  });
});

describe("money", () => {
  it("formats cents as dollars", () => {
    expect(formatMoney(40050)).toBe("$400.50");
  });
});
