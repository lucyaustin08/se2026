import type { GigStatus, GigType, Role } from "./api/types";

export const ROLE_LABELS: Record<Role, string> = {
  rhythm_guitar_vocals: "Rhythm guitar / vocals",
  lead_guitar: "Lead guitar",
  bass: "Bass",
  drums: "Drums",
  specialty: "Specialty instrument",
};

export const GIG_TYPE_LABELS: Record<GigType, string> = {
  full_band: "Full band",
  trio: "Trio",
  duo: "Duo",
};

export const GIG_STATUS_LABELS: Record<GigStatus, string> = {
  potential: "Potential",
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
  return timeFormat.format(new Date(iso)).replace(/ /g, " ");
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
