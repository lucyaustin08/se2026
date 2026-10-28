import type { ContactLabel, GigStatus, LineupSize, Role, SlotStatus } from "./api/types";

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
