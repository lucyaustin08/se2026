import { describe, expect, it } from "vitest";

import {
  addDays,
  addMonths,
  busyEntry,
  dayKey,
  entriesOn,
  gigEntry,
  initials,
  parseDayKey,
  practiceEntry,
  viewTitle,
  visibleDays,
  type CalendarEntry,
} from "./calendar";
import { caseyAway, garagePractice, hubCity, toListItem, toPeriod } from "./test/fixtures";

// Tests run in America/New_York (see vite.config.ts).
const day = (key: string) => parseDayKey(key) as Date;

describe("calendar days", () => {
  it("reads and writes local day keys, and rejects days that don't exist", () => {
    expect(dayKey(day("2026-11-12"))).toBe("2026-11-12");
    expect(parseDayKey("2026-02-30")).toBeNull();
    expect(parseDayKey("next tuesday")).toBeNull();
    expect(parseDayKey(null)).toBeNull();
  });

  it("adds days across the end of daylight saving without drifting off midnight", () => {
    const next = addDays(day("2026-10-31"), 2);
    expect(dayKey(next)).toBe("2026-11-02");
    expect(next.getHours()).toBe(0);
  });

  it("keeps a month step inside the target month", () => {
    expect(dayKey(addMonths(day("2027-01-31"), 1))).toBe("2027-02-28");
    expect(dayKey(addMonths(day("2026-11-12"), -1))).toBe("2026-10-12");
  });

  it("shows whole weeks, Sunday to Saturday, covering the month", () => {
    const days = visibleDays(day("2026-11-12"), "month");
    expect(days).toHaveLength(35);
    expect(dayKey(days[0])).toBe("2026-11-01");
    expect(dayKey(days[34])).toBe("2026-12-05");
  });

  it("shows the Sunday-to-Saturday week around the chosen day", () => {
    const days = visibleDays(day("2026-11-12"), "week");
    expect(days.map(dayKey)).toEqual([
      "2026-11-08",
      "2026-11-09",
      "2026-11-10",
      "2026-11-11",
      "2026-11-12",
      "2026-11-13",
      "2026-11-14",
    ]);
  });

  it("names the month or the week", () => {
    expect(viewTitle(day("2026-11-12"), "month")).toBe("November 2026");
    expect(viewTitle(day("2026-11-12"), "week")).toBe("Nov 8 – Nov 14, 2026");
  });
});

describe("calendar entries", () => {
  it("puts a busy time on every day it touches", () => {
    const entries = [busyEntry(toPeriod(caseyAway))];
    expect(
      ["2026-11-12", "2026-11-13", "2026-11-14", "2026-11-15", "2026-11-16"].map(
        (key) => entriesOn(day(key), entries).length,
      ),
    ).toEqual([0, 1, 1, 1, 0]);
  });

  it("puts a gig on the local day of its first set, and lists a day in time order", () => {
    const gig = gigEntry(toListItem(hubCity)) as CalendarEntry;
    const practice = practiceEntry({ ...garagePractice, starts_at: "2026-11-02T15:00:00Z" });
    // Hub City's first set is 1:00 AM UTC on Nov 3, which is 8:00 PM on Nov 2 locally.
    expect(entriesOn(day("2026-11-02"), [gig, practice]).map((e) => e.kind)).toEqual([
      "practice",
      "gig",
    ]);
    expect(entriesOn(day("2026-11-03"), [gig])).toEqual([]);
  });

  it("describes gigs plainly and leaves out cancelled ones", () => {
    expect(gigEntry(toListItem(hubCity))?.detail).toBe(
      "Gig (pending): Hub City Tap, first set at 8:00 PM",
    );
    expect(gigEntry({ ...toListItem(hubCity), restricted: true, venue_name: null })?.label).toBe(
      "8:00 PM Not assigned",
    );
    expect(gigEntry({ ...toListItem(hubCity), status: "cancelled" })).toBeNull();
  });

  it("labels busy times with the member's initials", () => {
    expect(busyEntry(toPeriod(caseyAway)).label).toBe("CM Busy");
    expect(busyEntry(toPeriod(caseyAway)).detail).toBe("Casey Morgan is busy, 9:00 AM – 6:00 PM");
    expect(initials("Riley  Chen-Park")).toBe("RC");
  });

  it("says a day of a weekly busy time repeats, and keys each day apart", () => {
    const wednesday = {
      kind: "weekly" as const,
      source_id: 401,
      member: { id: 2, name: "Sam Rivera" },
      starts_at: "2026-11-18T23:00:00Z",
      ends_at: "2026-11-19T02:00:00Z",
    };
    const nextWeek = {
      ...wednesday,
      starts_at: "2026-11-25T23:00:00Z",
      ends_at: "2026-11-26T02:00:00Z",
    };

    expect(busyEntry(wednesday).detail).toBe("Sam Rivera is busy, 6:00 PM – 9:00 PM, every week");
    expect(busyEntry(wednesday).key).not.toBe(busyEntry(nextWeek).key);
  });
});
