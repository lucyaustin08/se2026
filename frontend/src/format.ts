import type {
  ContactLabel,
  GigStatus,
  LineupSize,
  RecurringBusyTimeIn,
  Role,
  SlotStatus,
} from "./api/types";

export const ROLE_LABELS: Record<Role, string> = {
  rhythm_guitar_vocals: "Rhythm guitar / vocals",
  lead_guitar: "Lead guitar",
  bass: "Bass",
  drums: "Drums",
  specialty: "Specialty instrument",
};

/** The order roles are listed in everywhere. */
export const ROLES: readonly Role[] = [
  "rhythm_guitar_vocals",
  "lead_guitar",
  "bass",
  "drums",
  "specialty",
];

export const LINEUP_SIZE_LABELS: Record<LineupSize, string> = {
  solo: "Solo",
  duo: "Duo",
  trio: "Trio",
  quartet: "Quartet",
  full_band: "Full band",
};

export const SLOT_STATUS_LABELS: Record<SlotStatus, string> = {
  open: "Open",
  invited: "Invited, waiting for an answer",
  accepted: "Accepted",
  declined: "Declined",
};

export const CONTACT_LABELS: Record<ContactLabel, string> = {
  venue: "Venue",
  booking: "Booking",
  other: "Other",
};

export const GIG_STATUS_LABELS: Record<GigStatus, string> = {
  potential: "Pending",
  booked: "Booked",
  cancelled: "Cancelled",
};

const dateFormat = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
});
const timeFormat = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" });
const moneyFormat = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

/** "Sun, Oct 18, 2026", in the browser's time zone. */
export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

/** "8:00 PM", in the browser's time zone. */
export function formatTime(iso: string): string {
  // Newer ICU puts a narrow no-break space before AM/PM. Use a plain space everywhere.
  return timeFormat.format(new Date(iso)).replace(/\u202f/g, " ");
}

/** "$400.00" */
export function formatMoney(cents: number): string {
  return moneyFormat.format(cents / 100);
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** The browser-local "YYYY-MM-DD" a date input expects. */
export function toDateInputValue(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** The browser-local "HH:MM" a time input expects. */
export function toTimeInputValue(iso: string): string {
  const d = new Date(iso);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** A browser-local date and time from the form, as a UTC ISO 8601 string for the API. */
export function localInputsToIso(date: string, time: string): string {
  return new Date(`${date}T${time}`).toISOString();
}

/**
 * A stretch of time in the browser's time zone. On one day: "Sun, Oct 18, 2026, 6:00 PM – 9:00 PM".
 * Across days: "Sun, Oct 18, 2026, 6:00 PM – Tue, Oct 20, 2026, 9:00 AM".
 */
export function formatRange(startIso: string, endIso: string): string {
  const start = `${formatDate(startIso)}, ${formatTime(startIso)}`;
  if (toDateInputValue(startIso) === toDateInputValue(endIso)) {
    return `${start} – ${formatTime(endIso)}`;
  }
  return `${start} – ${formatDate(endIso)}, ${formatTime(endIso)}`;
}

/** Days of the week as the API numbers them (ISO): 1 is Monday, 7 is Sunday. */
export const ISO_WEEKDAYS: readonly { day: number; short: string; long: string }[] = [
  { day: 1, short: "Mon", long: "Monday" },
  { day: 2, short: "Tue", long: "Tuesday" },
  { day: 3, short: "Wed", long: "Wednesday" },
  { day: 4, short: "Thu", long: "Thursday" },
  { day: 5, short: "Fri", long: "Friday" },
  { day: 6, short: "Sat", long: "Saturday" },
  { day: 7, short: "Sun", long: "Sunday" },
];

/** "Every day", "Weekdays", "Weekends", or the days themselves: "Tue, Thu". */
export function formatWeekdays(days: number[]): string {
  const chosen = ISO_WEEKDAYS.filter(({ day }) => days.includes(day));
  const key = chosen.map(({ day }) => day).join(",");
  if (key === "1,2,3,4,5,6,7") return "Every day";
  if (key === "1,2,3,4,5") return "Weekdays";
  if (key === "6,7") return "Weekends";
  return chosen.map(({ short }) => short).join(", ");
}

/** "6:00 PM" from a clock time the API sends as "18:00:00". */
export function formatClockTime(clock: string): string {
  const [hours, minutes] = clock.split(":").map(Number);
  return formatTime(new Date(2000, 0, 1, hours, minutes).toISOString());
}

/** "Sun, Nov 1, 2026" from a date the API sends as "2026-11-01". */
export function formatPlainDate(day: string): string {
  // Read it as a local date: "2026-11-01" on its own would be midnight UTC, the day before here.
  return dateFormat.format(new Date(`${day}T00:00`));
}

type WeeklyTimes = Pick<RecurringBusyTimeIn, "weekdays" | "start_time" | "end_time">;

/**
 * When a weekly busy time happens: "Weekdays, 8:00 AM – 5:00 PM". One that runs past midnight
 * says so: "Sat, 10:00 PM – 2:00 AM the next day".
 */
export function formatWeeklyTimes(rule: WeeklyTimes): string {
  // "HH:MM:SS" strings sort the same way as the times they name.
  const overnight = rule.end_time <= rule.start_time;
  const times = `${formatClockTime(rule.start_time)} – ${formatClockTime(rule.end_time)}`;
  return `${formatWeekdays(rule.weekdays)}, ${times}${overnight ? " the next day" : ""}`;
}

/** "Starting Sun, Nov 1, 2026" or "Sun, Nov 1, 2026 to Thu, Dec 31, 2026". */
export function formatWeeklyDates(
  rule: Pick<RecurringBusyTimeIn, "starts_on" | "ends_on">,
): string {
  return rule.ends_on
    ? `${formatPlainDate(rule.starts_on)} to ${formatPlainDate(rule.ends_on)}`
    : `Starting ${formatPlainDate(rule.starts_on)}`;
}
