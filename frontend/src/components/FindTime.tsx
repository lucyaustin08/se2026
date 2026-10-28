import { useMutation } from "@tanstack/react-query";
import { useId, useState } from "react";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type { SuggestedTime } from "../api/types";
import { formatRange, toDateInputValue, toTimeInputValue } from "../format";
import { ErrorMessage } from "./QueryStates";
import { FormField, secondaryButton } from "./ui";

interface FindTimeProps {
  memberIds: number[];
  lengthMinutes: number;
  /** Fill the practice's date and start time from a suggestion. */
  onUse: (date: string, time: string) => void;
}

function toMinutes(value: string): number {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}

/**
 * Suggests practice times one to three weeks ahead: the best time on each day, with who
 * can't come. The scheduler still decides; picking one only fills in the form.
 */
export function FindTime({ memberIds, lengthMinutes, onUse }: FindTimeProps) {
  const formId = useId();
  const [earliest, setEarliest] = useState("17:00");
  const [latest, setLatest] = useState("23:00");
  const [hoursError, setHoursError] = useState<string | undefined>();
  const search = useMutation({
    mutationFn: () =>
      unwrap(
        api.GET("/api/v1/practices/suggestions", {
          params: {
            query: { member_ids: memberIds, length_minutes: lengthMinutes, earliest, latest },
          },
        }),
      ),
  });

  function find() {
    if (!earliest || !latest || toMinutes(latest) - toMinutes(earliest) < lengthMinutes) {
      setHoursError("Leave room for the whole practice between these times.");
      return;
    }
    setHoursError(undefined);
    search.mutate();
  }

  return (
    <section
      aria-labelledby={`${formId}-heading`}
      className="mt-4 border border-dashed border-gray-400 p-3"
    >
      <h3 id={`${formId}-heading`} className="font-semibold">
        Find a time
      </h3>
      <p className="mt-1 text-sm text-gray-700">
        Looks one to three weeks ahead for the time on each day that the most invitees can make.
      </p>
      <div className="mt-2 grid gap-3 sm:grid-cols-3 sm:items-end">
        <FormField
          id={`${formId}-earliest`}
          label="No earlier than"
          error={hoursError}
          input={(props) => (
            <input
              {...props}
              type="time"
              value={earliest}
              onChange={(event) => setEarliest(event.target.value)}
            />
          )}
        />
        <FormField
          id={`${formId}-latest`}
          label="Done by"
          input={(props) => (
            <input
              {...props}
              type="time"
              value={latest}
              onChange={(event) => setLatest(event.target.value)}
            />
          )}
        />
        <button
          type="button"
          className={secondaryButton}
          onClick={find}
          disabled={memberIds.length === 0 || search.isPending}
        >
          {search.isPending ? "Finding times…" : "Find times"}
        </button>
      </div>
      {memberIds.length === 0 && (
        <p className="mt-2 text-sm text-gray-700">Choose who's invited first.</p>
      )}
      {search.isError && (
        <div className="mt-3">
          <ErrorMessage message={errorMessage(search.error)} />
        </div>
      )}
      {search.isSuccess && (
        <Suggestions
          suggestions={search.data.suggestions}
          invitees={memberIds.length}
          onUse={(suggestion) =>
            onUse(toDateInputValue(suggestion.starts_at), toTimeInputValue(suggestion.starts_at))
          }
        />
      )}
    </section>
  );
}

function Suggestions({
  suggestions,
  invitees,
  onUse,
}: {
  suggestions: SuggestedTime[];
  invitees: number;
  onUse: (suggestion: SuggestedTime) => void;
}) {
  if (suggestions.length === 0) {
    return (
      <p className="mt-3 text-gray-700">
        Gigs fill every one of those times. Try different hours or a shorter practice.
      </p>
    );
  }
  return (
    <ol className="mt-3 space-y-2" aria-label="Suggested times, best first">
      {suggestions.slice(0, 8).map((suggestion) => {
        const everyone = suggestion.unavailable.length === 0;
        const range = formatRange(suggestion.starts_at, suggestion.ends_at);
        return (
          <li
            key={suggestion.starts_at}
            className={`flex flex-wrap items-center justify-between gap-2 px-3 py-2 ${everyone ? "border-2 border-ink" : "border border-gray-300"}`}
          >
            <span>
              <span className="block font-medium">{range}</span>
              <span className="block text-sm text-gray-700">
                {everyone
                  ? "Everyone can come."
                  : `${suggestion.available.length} of ${invitees} can come. Can't: ${suggestion.unavailable.map((m) => m.name).join(", ")}.`}
                {suggestion.same_day_gig && ` Gig that day: ${suggestion.same_day_gig}.`}
              </span>
            </span>
            <button
              type="button"
              className={secondaryButton}
              onClick={() => onUse(suggestion)}
              aria-label={`Use ${range}`}
            >
              Use this time
            </button>
          </li>
        );
      })}
    </ol>
  );
}
