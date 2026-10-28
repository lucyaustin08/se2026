import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import {
  addDays,
  addMonths,
  busyEntry,
  dayKey,
  entriesOn,
  gigEntry,
  initials,
  longDay,
  parseDayKey,
  practiceEntry,
  startOfDay,
  viewTitle,
  visibleDays,
  type CalendarEntry,
  type CalendarView,
  type EntryKind,
} from "../calendar";
import { ErrorMessage } from "../components/QueryStates";
import { secondaryButton } from "../components/ui";
import { memberFills, UNKNOWN_MEMBER_FILL } from "../memberColors";
import { runsTheBand, useActingMember } from "../session";
import { useMembers } from "./gigQueries";
import { usePractices } from "./PracticesSection";

const WEEKDAYS = [
  ["Sun", "Sunday"],
  ["Mon", "Monday"],
  ["Tue", "Tuesday"],
  ["Wed", "Wednesday"],
  ["Thu", "Thursday"],
  ["Fri", "Friday"],
  ["Sat", "Saturday"],
] as const;

const KIND_WORDS: Record<EntryKind, string> = { gig: "Gig", practice: "Practice", busy: "Busy" };
// On phones a day shows one letter per entry instead of the text.
const KIND_LETTERS: Record<EntryKind, string> = { gig: "G", practice: "P", busy: "B" };
const CELL_LIMIT = 3;
// The chosen view: tinted, heavier and underlined, so it doesn't rely on color alone.
const pressedButton =
  "min-h-11 border border-ink bg-brand-50 px-4 py-2 font-semibold text-ink underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600";

/**
 * Each kind has its own edge, so they read apart without color: a solid poster-red edge for
 * gigs, a solid navy edge for practices, and a dashed edge on the member's color for busy times.
 */
function entryStyle(entry: CalendarEntry, fills: Map<number, string>): string {
  if (entry.kind === "gig") return "border-l-4 border-poster-red bg-paper";
  if (entry.kind === "practice") return "border-l-4 border-navy bg-paper";
  const fill = (entry.memberId && fills.get(entry.memberId)) || UNKNOWN_MEMBER_FILL;
  return `border border-dashed border-ink ${fill}`;
}

function useCalendarData(rangeStart: string, rangeEnd: string) {
  const gigs = useQuery({
    queryKey: ["gigs", "calendar", rangeStart, rangeEnd],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/gigs", {
          params: {
            query: { first_set_after: rangeStart, first_set_before: rangeEnd, page_size: 100 },
          },
        }),
      ),
  });
  const practices = usePractices(rangeStart, rangeEnd);
  const busyTimes = useQuery({
    queryKey: ["busy-times", "calendar", rangeStart, rangeEnd],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/busy-times", {
          params: { query: { ends_after: rangeStart, starts_before: rangeEnd, page_size: 100 } },
        }),
      ),
  });
  const members = useMembers();
  return { gigs, practices, busyTimes, members };
}

export function BandCalendar() {
  const member = useActingMember();
  const [params, setParams] = useSearchParams();
  const view: CalendarView = params.get("view") === "week" ? "week" : "month";
  const today = startOfDay(new Date());
  const selected = parseDayKey(params.get("date")) ?? today;
  const days = visibleDays(selected, view);
  const rangeStart = days[0].toISOString();
  const rangeEnd = addDays(days[days.length - 1], 1).toISOString();
  const { gigs, practices, busyTimes, members } = useCalendarData(rangeStart, rangeEnd);

  const entries: CalendarEntry[] = [
    ...(gigs.data?.items ?? []).flatMap((gig) => gigEntry(gig) ?? []),
    ...(practices.data?.items ?? []).map(practiceEntry),
    ...(busyTimes.data?.items ?? []).map(busyEntry),
  ];
  const fills = memberFills(members.data?.items ?? []);
  const failed = [gigs, practices, busyTimes].filter((query) => query.isError);
  const loading = [gigs, practices, busyTimes].some((query) => query.isPending);

  // Arrow keys move the selected day; focus follows it once the new day has rendered.
  const moveFocus = useRef(false);
  const grid = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!moveFocus.current) return;
    moveFocus.current = false;
    grid.current?.querySelector<HTMLElement>(`[data-day="${dayKey(selected)}"]`)?.focus();
  });

  function go(date: Date, nextView: CalendarView = view) {
    setParams({ date: dayKey(date), view: nextView });
  }

  function handleDayKeys(event: KeyboardEvent<HTMLButtonElement>, day: Date) {
    const steps: Record<string, number> = {
      ArrowLeft: -1,
      ArrowRight: 1,
      ArrowUp: -7,
      ArrowDown: 7,
    };
    const step = steps[event.key];
    if (step === undefined) return;
    event.preventDefault();
    moveFocus.current = true;
    go(addDays(day, step));
  }

  const step = (direction: 1 | -1) =>
    view === "month" ? addMonths(selected, direction) : addDays(selected, 7 * direction);

  return (
    <section aria-labelledby="calendar-heading" className="mt-6">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-2 border-ink pb-2">
        {/* The poster moment: the month in Anton, big. Anton has one weight. */}
        <h2
          id="calendar-heading"
          className="font-display text-3xl leading-none tracking-wide uppercase sm:text-4xl"
          aria-live="polite"
        >
          {viewTitle(selected, view)}
        </h2>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Calendar view">
          {(["month", "week"] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={view === option}
              onClick={() => go(selected, option)}
              className={view === option ? pressedButton : secondaryButton}
            >
              {option === "month" ? "Month" : "Week"}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button type="button" className={secondaryButton} onClick={() => go(step(-1))}>
          {view === "month" ? "Previous month" : "Previous week"}
        </button>
        <button type="button" className={secondaryButton} onClick={() => go(today)}>
          Today
        </button>
        <button type="button" className={secondaryButton} onClick={() => go(step(1))}>
          {view === "month" ? "Next month" : "Next week"}
        </button>
        {loading && (
          <p role="status" className="text-sm text-gray-700">
            Loading the calendar…
          </p>
        )}
      </div>

      {failed.length > 0 && (
        <div className="mt-3">
          <ErrorMessage
            message={errorMessage(failed[0].error)}
            onRetry={() => failed.forEach((query) => void query.refetch())}
          />
        </div>
      )}

      <div ref={grid} className="mt-3">
        {view === "month" ? (
          <MonthGrid
            days={days}
            month={selected.getMonth()}
            selected={selected}
            today={today}
            entries={entries}
            fills={fills}
            onSelect={(day) => go(day)}
            onKeyDown={handleDayKeys}
          />
        ) : (
          <WeekList
            days={days}
            selected={selected}
            today={today}
            entries={entries}
            fills={fills}
            onSelect={(day) => go(day)}
            onKeyDown={handleDayKeys}
          />
        )}
      </div>

      <DayDetails day={selected} entries={entriesOn(selected, entries)} fills={fills} />
      <Legend
        players={(members.data?.items ?? []).filter(
          (m) => !m.is_manager && (runsTheBand(member) || m.id === member.id),
        )}
        fills={fills}
      />
    </section>
  );
}

interface DaysProps {
  days: Date[];
  selected: Date;
  today: Date;
  entries: CalendarEntry[];
  fills: Map<number, string>;
  onSelect: (day: Date) => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>, day: Date) => void;
}

function dayLabel(day: Date, count: number): string {
  if (count === 0) return longDay(day);
  return `${longDay(day)}, ${count} ${count === 1 ? "item" : "items"}`;
}

function MonthGrid({
  days,
  month,
  selected,
  today,
  entries,
  fills,
  onSelect,
  onKeyDown,
}: DaysProps & { month: number }) {
  const weeks = Array.from({ length: days.length / 7 }, (_, i) => days.slice(i * 7, i * 7 + 7));
  return (
    <table className="w-full table-fixed border-collapse">
      <thead>
        <tr>
          {WEEKDAYS.map(([short, full]) => (
            <th
              key={short}
              scope="col"
              className="pb-1 text-left text-sm font-medium text-gray-700"
            >
              <abbr title={full} className="no-underline">
                {short}
              </abbr>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {weeks.map((week) => (
          <tr key={dayKey(week[0])}>
            {week.map((day) => {
              const onDay = entriesOn(day, entries);
              const isSelected = dayKey(day) === dayKey(selected);
              const isToday = dayKey(day) === dayKey(today);
              const inMonth = day.getMonth() === month;
              return (
                <td
                  key={dayKey(day)}
                  className={`h-16 border border-gray-300 p-0 align-top sm:h-28 ${inMonth ? "bg-paper" : "bg-gray-100"}`}
                >
                  <button
                    type="button"
                    data-day={dayKey(day)}
                    tabIndex={isSelected ? 0 : -1}
                    aria-pressed={isSelected}
                    aria-current={isToday ? "date" : undefined}
                    aria-label={dayLabel(day, onDay.length)}
                    onClick={() => onSelect(day)}
                    onKeyDown={(event) => onKeyDown(event, day)}
                    className={`flex h-full w-full flex-col items-stretch gap-0.5 p-1 text-left hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600 ${isSelected ? "outline-2 -outline-offset-2 outline-ink" : ""}`}
                  >
                    <DayNumber day={day} isToday={isToday} muted={!inMonth} />
                    <span className="hidden flex-col gap-0.5 sm:flex">
                      {onDay.slice(0, CELL_LIMIT).map((entry) => (
                        <span
                          key={entry.key}
                          className={`truncate px-1 text-xs leading-5 text-ink ${entryStyle(entry, fills)}`}
                        >
                          {entry.label}
                        </span>
                      ))}
                      {onDay.length > CELL_LIMIT && (
                        <span className="px-1 text-xs text-gray-700">
                          +{onDay.length - CELL_LIMIT} more
                        </span>
                      )}
                    </span>
                    <span className="flex flex-wrap gap-0.5 sm:hidden">
                      {onDay.map((entry) => (
                        <span
                          key={entry.key}
                          className={`w-4 text-center text-[0.625rem] leading-4 font-semibold text-ink ${entryStyle(entry, fills)}`}
                        >
                          {KIND_LETTERS[entry.kind]}
                        </span>
                      ))}
                    </span>
                  </button>
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DayNumber({ day, isToday, muted }: { day: Date; isToday: boolean; muted: boolean }) {
  // Today is a filled red square with paper numerals, so it doesn't rely on color alone.
  if (isToday) {
    return (
      <span className="self-start bg-brand-700 px-1.5 text-sm font-semibold text-paper">
        {day.getDate()}
      </span>
    );
  }
  return (
    <span className={`text-sm font-medium ${muted ? "text-gray-600" : "text-ink"}`}>
      {day.getDate()}
    </span>
  );
}

function WeekList({ days, selected, today, entries, fills, onSelect, onKeyDown }: DaysProps) {
  return (
    <ol className="grid gap-2 sm:grid-cols-7 sm:gap-0">
      {days.map((day) => {
        const onDay = entriesOn(day, entries);
        const isSelected = dayKey(day) === dayKey(selected);
        const isToday = dayKey(day) === dayKey(today);
        return (
          <li
            key={dayKey(day)}
            className={`border border-gray-300 bg-paper sm:min-h-48 ${isSelected ? "outline-2 -outline-offset-2 outline-ink" : ""}`}
          >
            <button
              type="button"
              data-day={dayKey(day)}
              tabIndex={isSelected ? 0 : -1}
              aria-pressed={isSelected}
              aria-current={isToday ? "date" : undefined}
              aria-label={dayLabel(day, onDay.length)}
              onClick={() => onSelect(day)}
              onKeyDown={(event) => onKeyDown(event, day)}
              className="flex min-h-11 w-full items-center gap-2 border-b border-gray-300 px-2 py-1 text-left hover:bg-brand-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600"
            >
              <span className="text-sm text-gray-700">{WEEKDAYS[day.getDay()][0]}</span>
              <DayNumber day={day} isToday={isToday} muted={false} />
            </button>
            <ul className="space-y-1 p-1">
              {onDay.length === 0 && <li className="px-1 text-xs text-gray-600">Free</li>}
              {onDay.map((entry) => (
                <li
                  key={entry.key}
                  className={`px-1.5 py-0.5 text-xs text-ink ${entryStyle(entry, fills)}`}
                >
                  {entry.label}
                </li>
              ))}
            </ul>
          </li>
        );
      })}
    </ol>
  );
}

function DayDetails({
  day,
  entries,
  fills,
}: {
  day: Date;
  entries: CalendarEntry[];
  fills: Map<number, string>;
}) {
  return (
    <section aria-labelledby="day-heading" className="mt-4 border-t border-gray-300 pt-3">
      <h3 id="day-heading" className="font-semibold">
        {longDay(day)}
      </h3>
      {entries.length === 0 ? (
        <p className="mt-1 text-gray-700">Nothing on this day.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {entries.map((entry) => (
            <li key={entry.key} className={`px-3 py-2 text-ink ${entryStyle(entry, fills)}`}>
              <span className="mr-2 font-semibold">{KIND_WORDS[entry.kind]}</span>
              {entry.detail}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Legend({
  players,
  fills,
}: {
  players: { id: number; name: string }[];
  fills: Map<number, string>;
}) {
  return (
    <section aria-labelledby="legend-heading" className="mt-4 text-sm">
      <h3 id="legend-heading" className="font-semibold">
        Key
      </h3>
      <ul className="mt-1 flex flex-wrap gap-2">
        <li className="border-l-4 border-poster-red bg-paper px-2">Gig</li>
        <li className="border-l-4 border-navy bg-paper px-2">Practice</li>
        {players.map((player) => (
          <li
            key={player.id}
            className={`border border-dashed border-ink px-2 ${fills.get(player.id) ?? UNKNOWN_MEMBER_FILL}`}
          >
            <span className="font-semibold">{initials(player.name)}</span> {player.name} busy
          </li>
        ))}
      </ul>
    </section>
  );
}
