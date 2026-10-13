import { useId, useRef, useState, type FormEvent, type ReactNode } from "react";

import type { ContactIn, ContactLabel, GigCreate, GigDetail, Role } from "../api/types";
import {
  CONTACT_LABELS,
  localInputsToIso,
  ROLE_LABELS,
  ROLES,
  toDateInputValue,
  toTimeInputValue,
} from "../format";
import { ErrorMessage } from "./QueryStates";

export interface ContactValues {
  key: number;
  label: ContactLabel;
  name: string;
  phone: string;
  email: string;
  notes: string;
}

export interface GigFormValues {
  date: string;
  time: string;
  loadInMinutes: string;
  soundcheckMinutes: string;
  performanceMinutes: string;
  venueName: string;
  venueAddress: string;
  pay: string;
  roles: Role[];
  contacts: ContactValues[];
}

/** Errors by field name. Contact fields are named like `contacts.0.email`. */
export type GigFormErrors = Record<string, string>;

export const EMPTY_GIG_FORM: GigFormValues = {
  date: "",
  time: "",
  loadInMinutes: "120",
  soundcheckMinutes: "60",
  performanceMinutes: "180",
  venueName: "",
  venueAddress: "",
  pay: "",
  roles: [],
  contacts: [],
};

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;
const MINUTES_PATTERN = /^\d+$/;

function minutesError(raw: string, min: number, max: number): string | null {
  const value = raw.trim();
  if (!MINUTES_PATTERN.test(value) || Number(value) < min || Number(value) > max) {
    return `Enter whole minutes from ${min} to ${max}.`;
  }
  return null;
}

function isBlankContact(contact: ContactValues): boolean {
  return ![contact.name, contact.phone, contact.email, contact.notes].some((v) => v.trim());
}

/** Checks the browser can make early. The server re-checks everything. */
export function validateGigForm(values: GigFormValues): GigFormErrors {
  const errors: GigFormErrors = {};
  if (values.date && !values.time) errors.time = "Enter a first set time, or clear the date.";
  if (values.time && !values.date) errors.date = "Enter a date, or clear the first set time.";

  const minuteRules = [
    ["loadInMinutes", 0, 720],
    ["soundcheckMinutes", 0, 720],
    ["performanceMinutes", 15, 720],
  ] as const;
  for (const [field, min, max] of minuteRules) {
    const message = minutesError(values[field], min, max);
    if (message) errors[field] = message;
  }

  if (values.pay.trim() && !MONEY_PATTERN.test(values.pay.trim())) {
    errors.pay = "Enter pay as a dollar amount, like 400 or 400.50.";
  }
  values.contacts.forEach((contact, index) => {
    const email = contact.email.trim();
    if (email && !EMAIL_PATTERN.test(email)) {
      errors[`contacts.${index}.email`] = "Enter an email address like name@example.com.";
    }
  });
  return errors;
}

function textOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

/** The request body for a valid form. Empty fields are sent as null, which clears them. */
export function toGigBody(values: GigFormValues): GigCreate {
  const contacts: ContactIn[] = values.contacts
    .filter((contact) => !isBlankContact(contact))
    .map((contact) => ({
      label: contact.label,
      name: textOrNull(contact.name),
      phone: textOrNull(contact.phone),
      email: textOrNull(contact.email),
      notes: textOrNull(contact.notes),
    }));
  return {
    first_set_at: values.date && values.time ? localInputsToIso(values.date, values.time) : null,
    load_in_offset_minutes: Number(values.loadInMinutes.trim()),
    soundcheck_offset_minutes: Number(values.soundcheckMinutes.trim()),
    performance_minutes: Number(values.performanceMinutes.trim()),
    venue_name: textOrNull(values.venueName),
    venue_address: textOrNull(values.venueAddress),
    pay_cents: values.pay.trim() ? Math.round(Number(values.pay.trim()) * 100) : null,
    roles: ROLES.filter((role) => values.roles.includes(role)),
    contacts,
  };
}

export function gigToFormValues(gig: GigDetail): GigFormValues {
  return {
    date: gig.first_set_at ? toDateInputValue(gig.first_set_at) : "",
    time: gig.first_set_at ? toTimeInputValue(gig.first_set_at) : "",
    loadInMinutes: String(gig.load_in_offset_minutes),
    soundcheckMinutes: String(gig.soundcheck_offset_minutes),
    performanceMinutes: String(gig.performance_minutes),
    venueName: gig.venue_name ?? "",
    venueAddress: gig.venue_address ?? "",
    pay: gig.pay_cents === null ? "" : (gig.pay_cents / 100).toFixed(2),
    roles: gig.slots.map((slot) => slot.role),
    contacts: gig.contacts.map((contact, index) => ({
      key: index,
      label: contact.label,
      name: contact.name ?? "",
      phone: contact.phone ?? "",
      email: contact.email ?? "",
      notes: contact.notes ?? "",
    })),
  };
}

interface GigFormProps {
  initialValues?: GigFormValues;
  submitLabel: string;
  pending: boolean;
  serverError: string | null;
  onSubmit: (body: GigCreate) => void;
}

const inputClass =
  "mt-1 w-full rounded border px-3 py-2 focus-visible:outline-2 focus-visible:outline-brand-600";
const secondaryButton =
  "rounded border border-gray-400 px-3 py-1 text-sm hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-brand-600";

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
  const nextContactKey = useRef(initialValues.contacts.length);

  const fieldId = (field: string) => `${formId}-${field.replace(/\./g, "-")}`;

  function update<K extends keyof GigFormValues>(field: K, value: GigFormValues[K]) {
    setValues((previous) => ({ ...previous, [field]: value }));
  }

  function updateContact(index: number, field: keyof ContactValues, value: string) {
    setValues((previous) => ({
      ...previous,
      contacts: previous.contacts.map((contact, i) =>
        i === index ? { ...contact, [field]: value } : contact,
      ),
    }));
  }

  function addContact() {
    const key = nextContactKey.current++;
    update("contacts", [
      ...values.contacts,
      { key, label: "venue", name: "", phone: "", email: "", notes: "" },
    ]);
  }

  function removeContact(index: number) {
    update(
      "contacts",
      values.contacts.filter((_, i) => i !== index),
    );
    setErrors({});
  }

  function toggleRole(role: Role, checked: boolean) {
    update("roles", checked ? [...values.roles, role] : values.roles.filter((r) => r !== role));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validateGigForm(values);
    setErrors(found);
    const firstInvalid = Object.keys(found)[0];
    if (firstInvalid) {
      document.getElementById(fieldId(firstInvalid))?.focus();
      return;
    }
    onSubmit(toGigBody(values));
  }

  const textField = (
    field: Exclude<keyof GigFormValues, "roles" | "contacts">,
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
          {textField("date", "Date", { type: "date" })}
          {textField("time", "First set time", { type: "time" })}
          {textField("loadInMinutes", "Load-in (minutes before first set)", {
            inputMode: "numeric",
            hint: "Usually 120.",
          })}
          {textField("soundcheckMinutes", "Soundcheck (minutes before first set)", {
            inputMode: "numeric",
            hint: "Usually 60.",
          })}
          {textField("performanceMinutes", "Length (minutes from first set to the end)", {
            inputMode: "numeric",
            hint: "Usually 180.",
          })}
        </div>
      </Fieldset>

      <Fieldset legend="Where and pay">
        <div className="grid gap-4 sm:grid-cols-2">
          {textField("venueName", "Venue name")}
          {textField("venueAddress", "Venue address")}
          {textField("pay", "Total pay for the gig (USD)", { inputMode: "decimal" })}
        </div>
      </Fieldset>

      <Fieldset legend="Roles needed">
        <p className="text-sm text-gray-700">
          Pick every role this gig needs. Then invite members from the gig's page.
        </p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {ROLES.map((role) => (
            <label key={role} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={values.roles.includes(role)}
                onChange={(event) => toggleRole(role, event.target.checked)}
                className="h-4 w-4 focus-visible:outline-2 focus-visible:outline-brand-600"
              />
              {ROLE_LABELS[role]}
            </label>
          ))}
        </div>
      </Fieldset>

      <Fieldset legend="Contacts">
        {values.contacts.length === 0 && <p className="text-sm text-gray-700">No contacts yet.</p>}
        <ul className="space-y-4">
          {values.contacts.map((contact, index) => {
            const n = index + 1;
            const id = (field: string) => fieldId(`contacts.${index}.${field}`);
            return (
              <li key={contact.key} className="rounded border border-gray-200 p-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label htmlFor={id("label")} className="block font-medium">
                      Contact {n} type
                    </label>
                    <select
                      id={id("label")}
                      value={contact.label}
                      onChange={(event) => updateContact(index, "label", event.target.value)}
                      className={`${inputClass} border-gray-400`}
                    >
                      {(Object.keys(CONTACT_LABELS) as ContactLabel[]).map((label) => (
                        <option key={label} value={label}>
                          {CONTACT_LABELS[label]}
                        </option>
                      ))}
                    </select>
                  </div>
                  {(["name", "phone", "email"] as const).map((field) => (
                    <TextField
                      key={field}
                      id={id(field)}
                      label={`Contact ${n} ${field}`}
                      type={field === "email" ? "email" : field === "phone" ? "tel" : "text"}
                      value={contact[field]}
                      error={errors[`contacts.${index}.${field}`]}
                      onChange={(value) => updateContact(index, field, value)}
                    />
                  ))}
                  <div className="sm:col-span-2">
                    <label htmlFor={id("notes")} className="block font-medium">
                      Contact {n} notes
                    </label>
                    <textarea
                      id={id("notes")}
                      value={contact.notes}
                      rows={2}
                      onChange={(event) => updateContact(index, "notes", event.target.value)}
                      className={`${inputClass} border-gray-400`}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => removeContact(index)}
                  className={`${secondaryButton} mt-2`}
                >
                  Remove contact {n}
                </button>
              </li>
            );
          })}
        </ul>
        <button type="button" onClick={addContact} className={`${secondaryButton} mt-3`}>
          Add contact
        </button>
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

export function TextField({
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
        className={`${inputClass} ${error ? "border-red-700" : "border-gray-400"}`}
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
