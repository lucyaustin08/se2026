import { useId, useState, type FormEvent, type ReactNode } from "react";

import type { GigCreate, GigDetail, GigType } from "../api/types";
import { GIG_TYPE_LABELS, localInputsToIso, toDateInputValue, toTimeInputValue } from "../format";
import { ErrorMessage } from "./QueryStates";

export interface GigFormValues {
  date: string;
  time: string;
  loadInMinutes: string;
  soundcheckMinutes: string;
  venueName: string;
  venueAddress: string;
  gigType: GigType | "";
  pay: string;
  venueContactName: string;
  venueContactPhone: string;
  venueContactEmail: string;
  bookingContactName: string;
  bookingContactPhone: string;
  bookingContactEmail: string;
}

export type GigFormErrors = Partial<Record<keyof GigFormValues, string>>;

export const EMPTY_GIG_FORM: GigFormValues = {
  date: "",
  time: "",
  loadInMinutes: "120",
  soundcheckMinutes: "60",
  venueName: "",
  venueAddress: "",
  gigType: "",
  pay: "",
  venueContactName: "",
  venueContactPhone: "",
  venueContactEmail: "",
  bookingContactName: "",
  bookingContactPhone: "",
  bookingContactEmail: "",
};

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;
const MINUTES_PATTERN = /^\d+$/;
const MAX_OFFSET_MINUTES = 720;

/** Checks that only the browser can catch early. The server re-checks everything. */
export function validateGigForm(values: GigFormValues): GigFormErrors {
  const errors: GigFormErrors = {};
  if (values.date && !values.time) {
    errors.time = "Enter a first set time, or clear the date.";
  }
  if (values.time && !values.date) {
    errors.date = "Enter a date, or clear the first set time.";
  }
  for (const field of ["loadInMinutes", "soundcheckMinutes"] as const) {
    const raw = values[field].trim();
    if (!MINUTES_PATTERN.test(raw) || Number(raw) > MAX_OFFSET_MINUTES) {
      errors[field] = `Enter whole minutes from 0 to ${MAX_OFFSET_MINUTES}.`;
    }
  }
  if (values.pay.trim() && !MONEY_PATTERN.test(values.pay.trim())) {
    errors.pay = "Enter pay as a dollar amount, like 400 or 400.50.";
  }
  for (const field of ["venueContactEmail", "bookingContactEmail"] as const) {
    const raw = values[field].trim();
    if (raw && !EMAIL_PATTERN.test(raw)) {
      errors[field] = "Enter an email address like name@example.com.";
    }
  }
  return errors;
}

function textOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function contact(name: string, phone: string, email: string) {
  const result = { name: textOrNull(name), phone: textOrNull(phone), email: textOrNull(email) };
  return result.name || result.phone || result.email ? result : null;
}

/** The request body for a valid form. Empty fields are sent as null, which clears them. */
export function toGigBody(values: GigFormValues): GigCreate {
  return {
    first_set_at: values.date && values.time ? localInputsToIso(values.date, values.time) : null,
    load_in_offset_minutes: Number(values.loadInMinutes.trim()),
    soundcheck_offset_minutes: Number(values.soundcheckMinutes.trim()),
    venue_name: textOrNull(values.venueName),
    venue_address: textOrNull(values.venueAddress),
    gig_type: values.gigType || null,
    pay_cents: values.pay.trim() ? Math.round(Number(values.pay.trim()) * 100) : null,
    venue_contact: contact(
      values.venueContactName,
      values.venueContactPhone,
      values.venueContactEmail,
    ),
    booking_contact: contact(
      values.bookingContactName,
      values.bookingContactPhone,
      values.bookingContactEmail,
    ),
  };
}

export function gigToFormValues(gig: GigDetail): GigFormValues {
  return {
    date: gig.first_set_at ? toDateInputValue(gig.first_set_at) : "",
    time: gig.first_set_at ? toTimeInputValue(gig.first_set_at) : "",
    loadInMinutes: String(gig.load_in_offset_minutes),
    soundcheckMinutes: String(gig.soundcheck_offset_minutes),
    venueName: gig.venue_name ?? "",
    venueAddress: gig.venue_address ?? "",
    gigType: gig.gig_type ?? "",
    pay: gig.pay_cents === null ? "" : (gig.pay_cents / 100).toFixed(2),
    venueContactName: gig.venue_contact?.name ?? "",
    venueContactPhone: gig.venue_contact?.phone ?? "",
    venueContactEmail: gig.venue_contact?.email ?? "",
    bookingContactName: gig.booking_contact?.name ?? "",
    bookingContactPhone: gig.booking_contact?.phone ?? "",
    bookingContactEmail: gig.booking_contact?.email ?? "",
  };
}

interface GigFormProps {
  initialValues?: GigFormValues;
  submitLabel: string;
  pending: boolean;
  serverError: string | null;
  onSubmit: (body: GigCreate) => void;
}

export function GigForm({
  initialValues = EMPTY_GIG_FORM,
  submitLabel,
  pending,
  serverError,
  onSubmit,
}: GigFormProps) {
  const formId = useId();
  const [values, setValues] = useState<GigFormValues>(initialValues);
  const [errors, setErrors] = useState<GigFormErrors>({});

  const fieldId = (field: keyof GigFormValues) => `${formId}-${field}`;

  function update(field: keyof GigFormValues, value: string) {
    setValues((previous) => ({ ...previous, [field]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validateGigForm(values);
    setErrors(found);
    const firstInvalid = (Object.keys(EMPTY_GIG_FORM) as (keyof GigFormValues)[]).find(
      (field) => found[field],
    );
    if (firstInvalid) {
      document.getElementById(fieldId(firstInvalid))?.focus();
      return;
    }
    onSubmit(toGigBody(values));
  }

  const input = (
    field: keyof GigFormValues,
    label: string,
    options: { type?: string; inputMode?: "numeric" | "decimal"; hint?: string } = {},
  ) => (
    <TextField
      id={fieldId(field)}
      label={label}
      type={options.type}
      inputMode={options.inputMode}
      hint={options.hint}
      value={values[field]}
      error={errors[field]}
      onChange={(value) => update(field, value)}
    />
  );

  return (
    <form onSubmit={handleSubmit} noValidate className="max-w-2xl space-y-6">
      <p className="text-sm text-gray-700">
        Every field is optional while the gig is potential. Booking needs them filled in.
      </p>

      <Fieldset legend="When">
        <div className="grid gap-4 sm:grid-cols-2">
          {input("date", "Date", { type: "date" })}
          {input("time", "First set time", { type: "time" })}
          {input("loadInMinutes", "Load-in (minutes before first set)", {
            inputMode: "numeric",
            hint: "Usually 120.",
          })}
          {input("soundcheckMinutes", "Soundcheck (minutes before first set)", {
            inputMode: "numeric",
            hint: "Usually 60.",
          })}
        </div>
      </Fieldset>

      <Fieldset legend="Where and what">
        <div className="grid gap-4 sm:grid-cols-2">
          {input("venueName", "Venue name")}
          {input("venueAddress", "Venue address")}
          <div>
            <label htmlFor={fieldId("gigType")} className="block font-medium">
              Gig type
            </label>
            <select
              id={fieldId("gigType")}
              value={values.gigType}
              onChange={(event) => update("gigType", event.target.value)}
              className="mt-1 w-full rounded border border-gray-400 px-3 py-2 focus-visible:outline-2 focus-visible:outline-brand-600"
            >
              <option value="">Not set</option>
              {(Object.keys(GIG_TYPE_LABELS) as GigType[]).map((type) => (
                <option key={type} value={type}>
                  {GIG_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </div>
          {input("pay", "Pay (USD, whole gig)", { inputMode: "decimal" })}
        </div>
      </Fieldset>

      <Fieldset legend="Venue contact">
        <div className="grid gap-4 sm:grid-cols-3">
          {input("venueContactName", "Venue contact name")}
          {input("venueContactPhone", "Venue contact phone", { type: "tel" })}
          {input("venueContactEmail", "Venue contact email", { type: "email" })}
        </div>
      </Fieldset>

      <Fieldset legend="Booking contact (if different from the venue)">
        <div className="grid gap-4 sm:grid-cols-3">
          {input("bookingContactName", "Booking contact name")}
          {input("bookingContactPhone", "Booking contact phone", { type: "tel" })}
          {input("bookingContactEmail", "Booking contact email", { type: "email" })}
        </div>
      </Fieldset>

      {serverError && <ErrorMessage message={serverError} />}

      <button
        type="submit"
        disabled={pending}
        className="rounded bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60"
      >
        {pending ? "Saving…" : submitLabel}
      </button>
    </form>
  );
}

function Fieldset({ legend, children }: { legend: string; children: ReactNode }) {
  return (
    <fieldset className="rounded border border-gray-200 p-4">
      <legend className="px-1 font-semibold">{legend}</legend>
      {children}
    </fieldset>
  );
}

interface TextFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  inputMode?: "numeric" | "decimal";
  hint?: string;
  error?: string;
}

function TextField({
  id,
  label,
  value,
  onChange,
  type = "text",
  inputMode,
  hint,
  error,
}: TextFieldProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ");
  return (
    <div>
      <label htmlFor={id} className="block font-medium">
        {label}
      </label>
      <input
        id={id}
        type={type}
        inputMode={inputMode}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className={[
          "mt-1 w-full rounded border px-3 py-2 focus-visible:outline-2 focus-visible:outline-brand-600",
          error ? "border-red-700" : "border-gray-400",
        ].join(" ")}
      />
      {hint && (
        <p id={hintId} className="mt-1 text-sm text-gray-600">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1 text-sm font-medium text-red-800">
          {error}
        </p>
      )}
    </div>
  );
}
