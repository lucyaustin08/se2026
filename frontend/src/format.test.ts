import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatMoney,
  formatRange,
  formatClockTime,
  formatPlainDate,
  formatTime,
  formatWeekdays,
  formatWeeklyDates,
  formatWeeklyTimes,
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

describe("time ranges", () => {
  it("shows a range on one day with the date once", () => {
    expect(formatRange("2026-10-18T22:00:00Z", "2026-10-19T01:00:00Z")).toBe(
      "Sun, Oct 18, 2026, 6:00 PM – 9:00 PM",
    );
  });

  it("shows both dates for a range across days", () => {
    expect(formatRange("2026-10-18T22:00:00Z", "2026-10-20T13:00:00Z")).toBe(
      "Sun, Oct 18, 2026, 6:00 PM – Tue, Oct 20, 2026, 9:00 AM",
    );
  });
});

describe("money", () => {
  it("formats cents as dollars", () => {
    expect(formatMoney(40050)).toBe("$400.50");
  });
});

describe("weekly busy times", () => {
  it("names common sets of days in a word, and lists the rest Monday first", () => {
    expect(formatWeekdays([1, 2, 3, 4, 5, 6, 7])).toBe("Every day");
    expect(formatWeekdays([1, 2, 3, 4, 5])).toBe("Weekdays");
    expect(formatWeekdays([6, 7])).toBe("Weekends");
    expect(formatWeekdays([7, 2, 4])).toBe("Tue, Thu, Sun");
  });

  it("shows the API's clock times and dates as written, with no time zone shift", () => {
    expect(formatClockTime("08:00:00")).toBe("8:00 AM");
    expect(formatClockTime("18:30:00")).toBe("6:30 PM");
    // Read as midnight UTC, this would be the day before in New York.
    expect(formatPlainDate("2026-11-01")).toBe("Sun, Nov 1, 2026");
  });

  it("says when a weekly busy time runs past midnight", () => {
    expect(
      formatWeeklyTimes({
        weekdays: [1, 2, 3, 4, 5],
        start_time: "08:00:00",
        end_time: "17:00:00",
      }),
    ).toBe("Weekdays, 8:00 AM – 5:00 PM");
    expect(formatWeeklyTimes({ weekdays: [6], start_time: "22:00:00", end_time: "02:00:00" })).toBe(
      "Sat, 10:00 PM – 2:00 AM the next day",
    );
  });

  it("gives the dates it applies between, or just the first when it has no end", () => {
    expect(formatWeeklyDates({ starts_on: "2026-11-01", ends_on: null })).toBe(
      "Starting Sun, Nov 1, 2026",
    );
    expect(formatWeeklyDates({ starts_on: "2026-11-01", ends_on: "2026-12-31" })).toBe(
      "Sun, Nov 1, 2026 to Thu, Dec 31, 2026",
    );
  });
});
