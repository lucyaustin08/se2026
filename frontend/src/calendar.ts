/**
 * Calendar date math and entries, all in the browser's local time zone (see DECISIONS.md,
 * "Gig times entered in the browser's local time"). Pure functions, so they're easy to test.
 */
import type { BusyTimeOut, GigListItem, PracticeOut } from "./api/types";
import { formatTime } from "./format";

export type CalendarView = "month" | "week";

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "2026-11-12" for a local date. Also the format of `<input type="date">`. */
export function dayKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Local midnight on a "YYYY-MM-DD" day, or null if it isn't a real date. */
export function parseDayKey(key: string | null): Date | null {
  const match = key ? /^(\d{4})-(\d{2})-(\d{2})$/.exec(key) : null;
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return dayKey(date) === key ? date : null;
}

export function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/** Adds calendar days, so it stays on local midnight across daylight saving changes. */
export function addDays(date: Date, days: number): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

export function addMonths(date: Date, months: number): Date {
  // Clamp to the last day of the target month, so Jan 31 + 1 month is Feb 28, not Mar 3.
  const target = new Date(date.getFullYear(), date.getMonth() + months, 1);
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  return new Date(target.getFullYear(), target.getMonth(), Math.min(date.getDate(), lastDay));
}

/** The Sunday on or before `date`. Weeks start on Sunday, as on US calendars. */
export function startOfWeek(date: Date): Date {
  return addDays(startOfDay(date), -date.getDay());
}

/** Every day shown for the view: whole weeks covering the month, or one week. */
export function visibleDays(focus: Date, view: CalendarView): Date[] {
  if (view === "week") {
    const start = startOfWeek(focus);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }
  const first = new Date(focus.getFullYear(), focus.getMonth(), 1);
  const last = new Date(focus.getFullYear(), focus.getMonth() + 1, 0);
  const start = startOfWeek(first);
  const end = addDays(startOfWeek(last), 7);
  const days: Date[] = [];
  for (let day = start; day < end; day = addDays(day, 1)) days.push(day);
  return days;
}

const monthTitleFormat = new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" });
const shortDayFormat = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
const longDayFormat = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
  year: "numeric",
});

/** "November 2026", or "Nov 8 – Nov 14, 2026" for a week. */
export function viewTitle(focus: Date, view: CalendarView): string {
  if (view === "month") return monthTitleFormat.format(focus);
  const days = visibleDays(focus, "week");
  const last = days[6];
  return `${shortDayFormat.format(days[0])} – ${shortDayFormat.format(last)}, ${last.getFullYear()}`;
}

/** "Thursday, November 12, 2026" */
export function longDay(date: Date): string {
  return longDayFormat.format(date);
}

// ---- Entries --------------------------------------------------------------------------------

export type EntryKind = "gig" | "practice" | "busy";

export interface CalendarEntry {
  key: string;
  kind: EntryKind;
  start: Date;
  end: Date;
  /** Short text for a calendar cell. */
  label: string;
  /** Fuller text for the day's list. */
  detail: string;
  /** For busy times: whose they are. */
  memberId?: number;
  memberName?: string;
}

export function gigEntry(gig: GigListItem): CalendarEntry | null {
  if (!gig.first_set_at || gig.status === "cancelled") return null;
  const start = new Date(gig.first_set_at);
  const name = gig.restricted ? "Not assigned" : (gig.venue_name ?? "Untitled gig");
  const pending = gig.status === "potential" ? " (pending)" : "";
  return {
    key: `gig-${gig.id}`,
    kind: "gig",
    start,
    end: start,
    label: `${formatTime(gig.first_set_at)} ${name}`,
    detail: `Gig${pending}: ${name}, first set at ${formatTime(gig.first_set_at)}`,
  };
}

export function practiceEntry(practice: PracticeOut): CalendarEntry {
  const where = practice.location ? ` at ${practice.location}` : "";
  return {
    key: `practice-${practice.id}`,
    kind: "practice",
    start: new Date(practice.starts_at),
    end: new Date(practice.ends_at),
    label: `${formatTime(practice.starts_at)} Practice`,
    detail: `Practice${where}, ${formatTime(practice.starts_at)} – ${formatTime(practice.ends_at)}`,
  };
}

export function busyEntry(busyTime: BusyTimeOut): CalendarEntry {
  return {
    key: `busy-${busyTime.id}`,
    kind: "busy",
    start: new Date(busyTime.starts_at),
    end: new Date(busyTime.ends_at),
    label: `${initials(busyTime.member.name)} busy`,
    detail: `${busyTime.member.name} is busy, ${formatTime(busyTime.starts_at)} – ${formatTime(busyTime.ends_at)}`,
    memberId: busyTime.member.id,
    memberName: busyTime.member.name,
  };
}

/** "RC" for "Riley Chen". */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

/**
 * The entries on one local day, in time order. Anything running across midnight, like a
 * busy time over a weekend, shows on every day it touches.
 */
export function entriesOn(day: Date, entries: CalendarEntry[]): CalendarEntry[] {
  const dayStart = startOfDay(day);
  const dayEnd = addDays(dayStart, 1);
  return entries
    .filter((entry) =>
      entry.start.getTime() === entry.end.getTime()
        ? entry.start >= dayStart && entry.start < dayEnd
        : entry.start < dayEnd && entry.end > dayStart,
    )
    .sort((a, b) => a.start.getTime() - b.start.getTime() || a.key.localeCompare(b.key));
}
