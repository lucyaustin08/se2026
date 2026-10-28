import { useId, useState, type FormEvent } from "react";

import type { BusyTimeIn } from "../api/types";
import { localInputsToIso, toDateInputValue, toTimeInputValue } from "../format";
import { ErrorMessage } from "./QueryStates";
import { FormField, primaryButton, secondaryButton } from "./ui";

interface BusyTimeValues {
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
}

type BusyTimeField = keyof BusyTimeValues;
type BusyTimeErrors = Partial<Record<BusyTimeField, string>>;

const FIELD_ORDER: BusyTimeField[] = ["startDate", "startTime", "endDate", "endTime"];

export function validateBusyTime(values: BusyTimeValues): BusyTimeErrors {
  const errors: BusyTimeErrors = {};
  if (!values.startDate) errors.startDate = "Enter the date it starts.";
  if (!values.startTime) errors.startTime = "Enter the time it starts.";
  if (!values.endDate) errors.endDate = "Enter the date it ends.";
  if (!values.endTime) errors.endTime = "Enter the time it ends.";
  if (Object.keys(errors).length > 0) return errors;
  const start = localInputsToIso(values.startDate, values.startTime);
  const end = localInputsToIso(values.endDate, values.endTime);
  if (end <= start) errors.endTime = "The end has to be after the start.";
  return errors;
}

interface BusyTimeFormProps {
  /** Times to start from when changing an existing busy time. */
  initial?: { starts_at: string; ends_at: string };
  submitLabel: string;
  saving: boolean;
  saveError: string | null;
  onSave: (body: BusyTimeIn) => void;
  onCancel: () => void;
}

/** Start and end of a one-off busy time, each a date and a time in the browser's zone. */
export function BusyTimeForm({
  initial,
  submitLabel,
  saving,
  saveError,
  onSave,
  onCancel,
}: BusyTimeFormProps) {
  const formId = useId();
  const [values, setValues] = useState<BusyTimeValues>({
    startDate: initial ? toDateInputValue(initial.starts_at) : "",
    startTime: initial ? toTimeInputValue(initial.starts_at) : "",
    endDate: initial ? toDateInputValue(initial.ends_at) : "",
    endTime: initial ? toTimeInputValue(initial.ends_at) : "",
  });
  const [errors, setErrors] = useState<BusyTimeErrors>({});
  const fieldId = (field: BusyTimeField) => `${formId}-${field}`;

  function update(field: BusyTimeField, value: string) {
    setValues((current) => {
      const next = { ...current, [field]: value };
      // Most busy times end on the day they start, so fill that in until it's chosen.
      if (field === "startDate" && (!current.endDate || current.endDate === current.startDate)) {
        next.endDate = value;
      }
      return next;
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = validateBusyTime(values);
    setErrors(found);
    const firstInvalid = FIELD_ORDER.find((field) => found[field]);
    if (firstInvalid) {
      document.getElementById(fieldId(firstInvalid))?.focus();
      return;
    }
    onSave({
      starts_at: localInputsToIso(values.startDate, values.startTime),
      ends_at: localInputsToIso(values.endDate, values.endTime),
    });
  }

  const field = (name: BusyTimeField, label: string, type: "date" | "time") => (
    <FormField
      id={fieldId(name)}
      label={label}
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
      <fieldset>
        <legend className="text-sm font-semibold">Starts</legend>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {field("startDate", "Start date", "date")}
          {field("startTime", "Start time", "time")}
        </div>
      </fieldset>
      <fieldset className="mt-4">
        <legend className="text-sm font-semibold">Ends</legend>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {field("endDate", "End date", "date")}
          {field("endTime", "End time", "time")}
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
