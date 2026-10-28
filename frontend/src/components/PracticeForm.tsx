import { useId, useState, type FormEvent } from "react";

import type { MemberRead, PracticeCreate } from "../api/types";
import { localInputsToIso, ROLE_LABELS } from "../format";
import { FindTime } from "./FindTime";
import { ErrorMessage } from "./QueryStates";
import { FormField, primaryButton, secondaryButton } from "./ui";

const LENGTHS = [60, 90, 120, 150, 180, 210, 240];
const DEFAULT_LENGTH = 180;

function lengthLabel(minutes: number): string {
  const hours = minutes / 60;
  return `${hours} ${hours === 1 ? "hour" : "hours"}`;
}

interface PracticeValues {
  date: string;
  time: string;
  lengthMinutes: number;
  location: string;
  notes: string;
  memberIds: number[];
}

type PracticeField = "date" | "time" | "memberIds";
type PracticeErrors = Partial<Record<PracticeField, string>>;

export function validatePractice(values: PracticeValues): PracticeErrors {
  const errors: PracticeErrors = {};
  if (!values.date) errors.date = "Enter the practice date.";
  if (!values.time) errors.time = "Enter the start time.";
  if (values.memberIds.length === 0) errors.memberIds = "Invite at least one member.";
  return errors;
}

/** A gig conflict the server reported: refused outright, or a same-day warning to confirm. */
export type PracticeConflict = { kind: "overlap" | "same_day"; message: string } | null;

interface PracticeFormProps {
  players: MemberRead[];
  saving: boolean;
  conflict: PracticeConflict;
  saveError: string | null;
  onSave: (body: PracticeCreate) => void;
  onCancel: () => void;
  /** Called when the scheduler changes anything, so an old conflict message goes away. */
  onEdit: () => void;
}

export function PracticeForm({
  players,
  saving,
  conflict,
  saveError,
  onSave,
  onCancel,
  onEdit,
}: PracticeFormProps) {
  const formId = useId();
  const [values, setValues] = useState<PracticeValues>({
    date: "",
    time: "",
    lengthMinutes: DEFAULT_LENGTH,
    location: "",
    notes: "",
    memberIds: [],
  });
  const [errors, setErrors] = useState<PracticeErrors>({});
  const fieldId = (field: string) => `${formId}-${field}`;
  const inviteesErrorId = fieldId("memberIds-error");

  function update<K extends keyof PracticeValues>(field: K, value: PracticeValues[K]) {
    setValues((current) => ({ ...current, [field]: value }));
    onEdit();
  }

  function toggleMember(id: number, checked: boolean) {
    update(
      "memberIds",
      checked ? [...values.memberIds, id] : values.memberIds.filter((m) => m !== id),
    );
  }

  function body(confirmSameDay: boolean): PracticeCreate {
    return {
      starts_at: localInputsToIso(values.date, values.time),
      length_minutes: values.lengthMinutes,
      location: values.location.trim() || null,
      notes: values.notes.trim() || null,
      member_ids: values.memberIds,
      confirm_same_day: confirmSameDay,
    };
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const found = validatePractice(values);
    setErrors(found);
    const firstInvalid = (["date", "time", "memberIds"] as const).find((field) => found[field]);
    if (firstInvalid) {
      const target =
        firstInvalid === "memberIds"
          ? document.querySelector<HTMLInputElement>(`[name="${fieldId("member")}"]`)
          : document.getElementById(fieldId(firstInvalid));
      target?.focus();
      return;
    }
    onSave(body(false));
  }

  return (
    <form onSubmit={submit} noValidate>
      {saveError && (
        <div className="mb-4">
          <ErrorMessage message={saveError} />
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        <FormField
          id={fieldId("date")}
          label="Date"
          error={errors.date}
          input={(props) => (
            <input
              {...props}
              type="date"
              value={values.date}
              onChange={(event) => update("date", event.target.value)}
            />
          )}
        />
        <FormField
          id={fieldId("time")}
          label="Start time"
          error={errors.time}
          input={(props) => (
            <input
              {...props}
              type="time"
              value={values.time}
              onChange={(event) => update("time", event.target.value)}
            />
          )}
        />
        <FormField
          id={fieldId("length")}
          label="Length"
          input={(props) => (
            <select
              {...props}
              value={values.lengthMinutes}
              onChange={(event) => update("lengthMinutes", Number(event.target.value))}
            >
              {LENGTHS.map((minutes) => (
                <option key={minutes} value={minutes}>
                  {lengthLabel(minutes)}
                </option>
              ))}
            </select>
          )}
        />
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <FormField
          id={fieldId("location")}
          label="Location"
          hint="Optional."
          input={(props) => (
            <input
              {...props}
              value={values.location}
              onChange={(event) => update("location", event.target.value)}
            />
          )}
        />
        <FormField
          id={fieldId("notes")}
          label="Notes"
          hint="Optional. What to work on."
          input={(props) => (
            <input
              {...props}
              value={values.notes}
              onChange={(event) => update("notes", event.target.value)}
            />
          )}
        />
      </div>

      <fieldset
        className="mt-4"
        aria-describedby={errors.memberIds ? inviteesErrorId : undefined}
        aria-invalid={errors.memberIds ? true : undefined}
      >
        <legend className="text-sm font-semibold">Who's invited</legend>
        <ul className="mt-2 grid gap-1 sm:grid-cols-2">
          {players.map((player) => {
            const id = fieldId(`member-${player.id}`);
            return (
              <li key={player.id}>
                <label
                  htmlFor={id}
                  className="flex min-h-11 items-center gap-2 border border-gray-300 px-3 py-2 hover:bg-gray-100"
                >
                  <input
                    id={id}
                    name={fieldId("member")}
                    type="checkbox"
                    checked={values.memberIds.includes(player.id)}
                    onChange={(event) => toggleMember(player.id, event.target.checked)}
                    className="size-4 accent-brand-700"
                  />
                  <span>
                    {player.name}
                    {player.primary_role && (
                      <span className="text-sm text-gray-700">
                        {" "}
                        · {ROLE_LABELS[player.primary_role]}
                      </span>
                    )}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
        {errors.memberIds && (
          <p id={inviteesErrorId} className="mt-1 text-sm font-medium text-brand-700">
            {errors.memberIds}
          </p>
        )}
      </fieldset>

      <FindTime
        memberIds={values.memberIds}
        lengthMinutes={values.lengthMinutes}
        onUse={(date, time) => {
          setValues((current) => ({ ...current, date, time }));
          onEdit();
          document.getElementById(fieldId("date"))?.focus();
        }}
      />

      {conflict?.kind === "overlap" && (
        <div role="alert" className="mt-4 border-2 border-brand-700 bg-brand-50 p-3">
          <p className="font-semibold">Can't schedule this practice</p>
          <p className="mt-1">{conflict.message}</p>
        </div>
      )}

      {conflict?.kind === "same_day" ? (
        // A gig is on the same day: the scheduler confirms or goes back and changes the time.
        <div role="alert" className="mt-4 border-2 border-dashed border-mustard bg-paper p-3">
          <p className="font-semibold">Heads up: there's a gig that day</p>
          <p className="mt-1">{conflict.message}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              className={primaryButton}
              disabled={saving}
              onClick={() => onSave(body(true))}
            >
              Schedule anyway
            </button>
            <button
              type="button"
              className={secondaryButton}
              onClick={() => {
                onEdit();
                document.getElementById(fieldId("date"))?.focus();
              }}
            >
              Change the time
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-5 flex flex-wrap gap-3">
          <button type="submit" className={primaryButton} disabled={saving}>
            {saving ? "Scheduling…" : "Schedule practice"}
          </button>
          <button type="button" className={secondaryButton} onClick={onCancel}>
            Cancel
          </button>
        </div>
      )}
    </form>
  );
}
