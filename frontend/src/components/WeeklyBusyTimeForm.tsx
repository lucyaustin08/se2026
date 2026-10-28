import { useId, useState, type FormEvent } from "react";

import type { RecurringBusyTimeIn } from "../api/types";
import { ISO_WEEKDAYS } from "../format";
import { ErrorMessage } from "./QueryStates";
import { FormField, primaryButton, secondaryButton } from "./ui";

/** What the form fills in. The pop-up adds whether to decline overlapping invitations. */
export type WeeklyBusyTimeFields = Omit<RecurringBusyTimeIn, "decline_invitations">;

interface WeeklyValues {
  weekdays: number[];
  startTime: string;
  endTime: string;
  startsOn: string;
  endsOn: string;
}

type WeeklyField = keyof WeeklyValues;
type WeeklyErrors = Partial<Record<WeeklyField, string>>;

const FIELD_ORDER: WeeklyField[] = ["weekdays", "startTime", "endTime", "startsOn", "endsOn"];

export function validateWeeklyBusyTime(values: WeeklyValues): WeeklyErrors {
  const errors: WeeklyErrors = {};
  if (values.weekdays.length === 0) errors.weekdays = "Pick at least one day.";
  if (!values.startTime) errors.startTime = "Enter the time it starts.";
  if (!values.endTime) {
    errors.endTime = "Enter the time it ends.";
  } else if (values.endTime === values.startTime) {
    errors.endTime = "The end time has to be different from the start time.";
  }
  if (!values.startsOn) errors.startsOn = "Enter the first date.";
  // "YYYY-MM-DD" strings sort the same way as the dates they name.
  if (values.startsOn && values.endsOn && values.endsOn < values.startsOn) {
    errors.endsOn = "The last date can't be before the first date.";
  }
  return errors;
}

/** Today in the browser's time zone, as a date input expects it. */
function todayValue(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

interface WeeklyBusyTimeFormProps {
  /** The weekly busy time to start from when changing one. */
  initial?: WeeklyBusyTimeFields;
  submitLabel: string;
  saving: boolean;
  saveError: string | null;
  onSave: (body: WeeklyBusyTimeFields) => void;
  onCancel: () => void;
}

/**
 * A busy time that repeats every week: which days, from what time to what time, and the dates
 * it applies between. Times are the band's clock times, so 8:00 AM stays 8:00 AM all year.
 */
export function WeeklyBusyTimeForm({
  initial,
  submitLabel,
  saving,
  saveError,
  onSave,
  onCancel,
}: WeeklyBusyTimeFormProps) {
  const formId = useId();
  const [values, setValues] = useState<WeeklyValues>({
    weekdays: initial?.weekdays ?? [],
    // The API sends "18:00:00"; a time input wants "18:00".
    startTime: initial?.start_time.slice(0, 5) ?? "",
    endTime: initial?.end_time.slice(0, 5) ?? "",
    startsOn: initial?.starts_on ?? todayValue(),
    endsOn: initial?.ends_on ?? "",
  });
  const [errors, setErrors] = useState<WeeklyErrors>({});
  const fieldId = (field: Exclude<WeeklyField, "weekdays">) => `${formId}-${field}`;
  const dayId = (day: number) => `${formId}-day-${day}`;
  const daysErrorId = `${formId}-weekdays-error`;

  function update(field: Exclude<WeeklyField, "weekdays">, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function toggleDay(day: number, checked: boolean) {
    setValues((current) => ({
      ...current,
      weekdays: checked
        ? [...current.weekdays, day].sort((a, b) => a - b)
        : current.weekdays.filter((d) => d !== day),
    }));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = validateWeeklyBusyTime(values);
    setErrors(found);
    const firstInvalid = FIELD_ORDER.find((field) => found[field]);
    if (firstInvalid) {
      const target = firstInvalid === "weekdays" ? dayId(1) : fieldId(firstInvalid);
      document.getElementById(target)?.focus();
      return;
    }
    onSave({
      weekdays: values.weekdays,
      start_time: values.startTime,
      end_time: values.endTime,
      starts_on: values.startsOn,
      ends_on: values.endsOn || null,
    });
  }

  const field = (
    name: Exclude<WeeklyField, "weekdays">,
    label: string,
    type: "date" | "time",
    hint?: string,
  ) => (
    <FormField
      id={fieldId(name)}
      label={label}
      hint={hint}
      error={errors[name]}
      input={(props) => (
        <input
          {...props}
          type={type}
          value={values[name]}
          onChange={(event) => update(name, event.target.value)}
        />
      )}
    />
  );

  return (
    <form onSubmit={submit} noValidate>
      {saveError && (
        <div className="mb-4">
          <ErrorMessage message={saveError} />
        </div>
      )}
      <fieldset aria-describedby={errors.weekdays ? daysErrorId : undefined}>
        <legend className="text-sm font-semibold">Days</legend>
        <div className="mt-2 grid grid-cols-2 gap-x-3 sm:grid-cols-4">
          {ISO_WEEKDAYS.map(({ day, long }) => (
            <label key={day} htmlFor={dayId(day)} className="flex min-h-11 items-center gap-2">
              <input
                id={dayId(day)}
                type="checkbox"
                className="size-5 accent-brand-700"
                checked={values.weekdays.includes(day)}
                onChange={(event) => toggleDay(day, event.target.checked)}
                aria-invalid={errors.weekdays ? true : undefined}
              />
              {long}
            </label>
          ))}
        </div>
        {errors.weekdays && (
          <p id={daysErrorId} className="mt-1 text-sm font-medium text-brand-700">
            {errors.weekdays}
          </p>
        )}
      </fieldset>
      <fieldset className="mt-4">
        <legend className="text-sm font-semibold">Times</legend>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {field("startTime", "Start time", "time")}
          {field(
            "endTime",
            "End time",
            "time",
            "Earlier than the start time means it runs past midnight.",
          )}
        </div>
      </fieldset>
      <fieldset className="mt-4">
        <legend className="text-sm font-semibold">Dates</legend>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {field("startsOn", "First date", "date")}
          {field("endsOn", "Last date", "date", "Optional. Leave it empty to keep it going.")}
        </div>
      </fieldset>
      <div className="mt-5 flex flex-wrap gap-3">
        <button type="submit" className={primaryButton} disabled={saving}>
          {saving ? "Saving…" : submitLabel}
        </button>
        <button type="button" className={secondaryButton} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
