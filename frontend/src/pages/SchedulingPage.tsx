import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type {
  BusyTimeIn,
  BusyTimeOut,
  RecurringBusyTimeIn,
  RecurringBusyTimeOut,
} from "../api/types";
import { BusyTimeForm } from "../components/BusyTimeForm";
import { Dialog } from "../components/Dialog";
import { ErrorMessage, Loading } from "../components/QueryStates";
import { pageHeading, primaryButton, secondaryButton, sectionHeading } from "../components/ui";
import { WeeklyBusyTimeForm } from "../components/WeeklyBusyTimeForm";
import { formatRange, formatWeeklyDates, formatWeeklyTimes } from "../format";
import { runsTheBand, useActingMember } from "../session";
import { BandCalendar } from "./BandCalendar";
import { PracticesSection } from "./PracticesSection";

const BUSY_TIMES_KEY = ["busy-times"] as const;
const PAGE_SIZE = 100;

export function SchedulingPage() {
  const member = useActingMember();
  // "Upcoming" means anything that hasn't ended when the page opened.
  const [now] = useState(() => new Date().toISOString());

  return (
    <section>
      <h1 className={pageHeading}>Scheduling</h1>
      <p className="mt-1 text-gray-700">
        Practices, and when people can't play. Anyone without busy times counts as available.
      </p>
      <BandCalendar />
      <PracticesSection now={now} />
      {/* The manager doesn't play, so has no busy times of their own. */}
      {!member.isManager && <MyBusyTimes now={now} />}
      {runsTheBand(member) && <BandBusyTimes now={now} />}
    </section>
  );
}

function useBusyTimes(now: string, memberId?: number) {
  return useQuery({
    queryKey: [...BUSY_TIMES_KEY, memberId ?? "everyone", now],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/busy-times", {
          params: {
            query: {
              ends_after: now,
              page_size: PAGE_SIZE,
              ...(memberId ? { member_id: memberId } : {}),
            },
          },
        }),
      ),
  });
}

/** Weekly busy times, kept under the busy-times key so one refresh covers everything. */
function useWeeklyBusyTimes(memberId?: number) {
  return useQuery({
    queryKey: [...BUSY_TIMES_KEY, "weekly", memberId ?? "everyone"],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/recurring-busy-times", {
          params: {
            query: { page_size: PAGE_SIZE, ...(memberId ? { member_id: memberId } : {}) },
          },
        }),
      ),
  });
}

type Editing =
  | { kind: "add" }
  | { kind: "change"; busyTime: BusyTimeOut }
  | { kind: "change-weekly"; rule: RecurringBusyTimeOut }
  | null;

function MyBusyTimes({ now }: { now: string }) {
  const member = useActingMember();
  const oneOff = useBusyTimes(now, member.id);
  const weekly = useWeeklyBusyTimes(member.id);
  const [editing, setEditing] = useState<Editing>(null);
  const failed = [oneOff, weekly].find((query) => query.isError);

  return (
    <section aria-labelledby="mine-heading" className="mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="mine-heading" className={sectionHeading}>
          Your busy times
        </h2>
        <button type="button" className={primaryButton} onClick={() => setEditing({ kind: "add" })}>
          Add busy time
        </button>
      </div>
      <div className="mt-3">
        {failed ? (
          <ErrorMessage
            message={errorMessage(failed.error)}
            onRetry={() => void failed.refetch()}
          />
        ) : (
          (oneOff.isPending || weekly.isPending) && <Loading label="Loading your busy times…" />
        )}
        {oneOff.isSuccess &&
          weekly.isSuccess &&
          (oneOff.data.items.length === 0 && weekly.data.items.length === 0 ? (
            <p className="text-gray-700">
              You haven't marked any busy times, so you count as available.
            </p>
          ) : (
            <div className="space-y-4">
              {weekly.data.items.length > 0 && (
                <div>
                  <h3 className="font-semibold">Every week</h3>
                  <ul className="mt-2 space-y-2">
                    {weekly.data.items.map((rule) => (
                      <WeeklyBusyTimeRow
                        key={rule.id}
                        rule={rule}
                        onChange={() => setEditing({ kind: "change-weekly", rule })}
                      />
                    ))}
                  </ul>
                  <MoreNote page={weekly.data} noun="weekly busy times" />
                </div>
              )}
              {oneOff.data.items.length > 0 && (
                <div>
                  <h3 className="font-semibold">One-off</h3>
                  <ul className="mt-2 space-y-2">
                    {oneOff.data.items.map((busyTime) => (
                      <MyBusyTimeRow
                        key={busyTime.id}
                        busyTime={busyTime}
                        onChange={() => setEditing({ kind: "change", busyTime })}
                      />
                    ))}
                  </ul>
                  <MoreNote page={oneOff.data} noun="busy times" />
                </div>
              )}
            </div>
          ))}
      </div>
      {editing && <BusyTimeDialog editing={editing} onClose={() => setEditing(null)} />}
    </section>
  );
}

const rowClass =
  "flex flex-wrap items-center justify-between gap-3 border border-gray-300 bg-paper px-4 py-3";
const tagClass = "mr-2 inline-block border border-dashed border-ink px-1.5 text-sm font-medium";

function RowButtons({
  what,
  onChange,
  onDelete,
  deleting,
}: {
  what: string;
  onChange: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <span className="flex gap-2">
      <button
        type="button"
        className={secondaryButton}
        onClick={onChange}
        aria-label={`Change ${what}`}
      >
        Change
      </button>
      <button
        type="button"
        className={secondaryButton}
        onClick={onDelete}
        disabled={deleting}
        aria-label={`Delete ${what}`}
      >
        Delete
      </button>
    </span>
  );
}

function MyBusyTimeRow({ busyTime, onChange }: { busyTime: BusyTimeOut; onChange: () => void }) {
  const queryClient = useQueryClient();
  const range = formatRange(busyTime.starts_at, busyTime.ends_at);
  const remove = useMutation({
    mutationFn: () =>
      unwrap(
        api.DELETE("/api/v1/busy-times/{busy_time_id}", {
          params: { path: { busy_time_id: busyTime.id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: BUSY_TIMES_KEY }),
  });

  return (
    <li className={rowClass}>
      <span>
        <span className={tagClass}>Busy</span>
        {range}
      </span>
      <RowButtons
        what={`busy time ${range}`}
        onChange={onChange}
        onDelete={() => remove.mutate()}
        deleting={remove.isPending}
      />
      {remove.isError && (
        <div className="w-full">
          <ErrorMessage message={errorMessage(remove.error)} />
        </div>
      )}
    </li>
  );
}

function WeeklyBusyTimeRow({
  rule,
  onChange,
}: {
  rule: RecurringBusyTimeOut;
  onChange: () => void;
}) {
  const queryClient = useQueryClient();
  const times = formatWeeklyTimes(rule);
  const remove = useMutation({
    mutationFn: () =>
      unwrap(
        api.DELETE("/api/v1/recurring-busy-times/{rule_id}", {
          params: { path: { rule_id: rule.id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: BUSY_TIMES_KEY }),
  });

  return (
    <li className={rowClass}>
      <span>
        <span className={tagClass}>Weekly</span>
        <span>{times}</span>
        <span className="block text-sm text-gray-700">{formatWeeklyDates(rule)}</span>
      </span>
      <RowButtons
        what={`weekly busy time ${times}`}
        onChange={onChange}
        onDelete={() => remove.mutate()}
        deleting={remove.isPending}
      />
      {remove.isError && (
        <div className="w-full">
          <ErrorMessage message={errorMessage(remove.error)} />
        </div>
      )}
    </li>
  );
}

function BusyTimeDialog({
  editing,
  onClose,
}: {
  editing: NonNullable<Editing>;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  // Only a new busy time can choose; a change keeps the kind it already is.
  const [repeats, setRepeats] = useState(false);
  const weekly = editing.kind === "add" ? repeats : editing.kind === "change-weekly";
  const done = () => {
    void queryClient.invalidateQueries({ queryKey: BUSY_TIMES_KEY });
    onClose();
  };
  const saveOneOff = useMutation({
    mutationFn: (body: BusyTimeIn) =>
      editing.kind === "change"
        ? unwrap(
            api.PATCH("/api/v1/busy-times/{busy_time_id}", {
              params: { path: { busy_time_id: editing.busyTime.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/busy-times", { body })),
    onSuccess: done,
  });
  const saveWeekly = useMutation({
    mutationFn: (body: RecurringBusyTimeIn) =>
      editing.kind === "change-weekly"
        ? unwrap(
            api.PATCH("/api/v1/recurring-busy-times/{rule_id}", {
              params: { path: { rule_id: editing.rule.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/recurring-busy-times", { body })),
    onSuccess: done,
  });
  const title =
    editing.kind === "add"
      ? "Add busy time"
      : weekly
        ? "Change weekly busy time"
        : "Change busy time";
  const submitLabel = editing.kind === "add" ? "Add busy time" : "Save changes";

  return (
    <Dialog title={title} onClose={onClose}>
      {editing.kind === "add" && (
        <fieldset className="mb-4">
          <legend className="text-sm font-semibold">How often</legend>
          <div className="mt-2 flex flex-wrap gap-x-6">
            {[
              { value: false, label: "One-off" },
              { value: true, label: "Repeats weekly" },
            ].map((option) => (
              <label key={option.label} className="flex min-h-11 items-center gap-2">
                <input
                  type="radio"
                  name="how-often"
                  className="size-5 accent-brand-700"
                  checked={repeats === option.value}
                  onChange={() => setRepeats(option.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <p className="mb-4 text-sm text-gray-700">
        {weekly
          ? "The same hours every week, like a job or a class. Times are the band's local time."
          : "A one-off stretch of time you can't play. It can run over several days."}
      </p>
      {weekly ? (
        <WeeklyBusyTimeForm
          initial={editing.kind === "change-weekly" ? editing.rule : undefined}
          submitLabel={submitLabel}
          saving={saveWeekly.isPending}
          saveError={saveWeekly.isError ? errorMessage(saveWeekly.error) : null}
          onSave={(body) => saveWeekly.mutate(body)}
          onCancel={onClose}
        />
      ) : (
        <BusyTimeForm
          initial={editing.kind === "change" ? editing.busyTime : undefined}
          submitLabel={submitLabel}
          saving={saveOneOff.isPending}
          saveError={saveOneOff.isError ? errorMessage(saveOneOff.error) : null}
          onSave={(body) => saveOneOff.mutate(body)}
          onCancel={onClose}
        />
      )}
    </Dialog>
  );
}

function BandBusyTimes({ now }: { now: string }) {
  const oneOff = useBusyTimes(now);
  const weekly = useWeeklyBusyTimes();
  const failed = [oneOff, weekly].find((query) => query.isError);

  return (
    <section aria-labelledby="band-heading" className="mt-8">
      <h2 id="band-heading" className={sectionHeading}>
        Everyone's busy times
      </h2>
      <p className="mt-1 text-sm text-gray-700">Only the manager and band leader see these.</p>
      <div className="mt-3">
        {failed ? (
          <ErrorMessage
            message={errorMessage(failed.error)}
            onRetry={() => void failed.refetch()}
          />
        ) : (
          (oneOff.isPending || weekly.isPending) && (
            <Loading label="Loading the band's busy times…" />
          )
        )}
        {oneOff.isSuccess &&
          weekly.isSuccess &&
          (oneOff.data.items.length === 0 && weekly.data.items.length === 0 ? (
            <p className="text-gray-700">
              Nobody has marked any busy times. Everyone is available.
            </p>
          ) : (
            <>
              <BusyTimesByMember oneOff={oneOff.data.items} weekly={weekly.data.items} />
              <MoreNote page={weekly.data} noun="weekly busy times" />
              <MoreNote page={oneOff.data} noun="busy times" />
            </>
          ))}
      </div>
    </section>
  );
}

interface MemberBusyTimes {
  name: string;
  weekly: RecurringBusyTimeOut[];
  oneOff: BusyTimeOut[];
}

function BusyTimesByMember({
  oneOff,
  weekly,
}: {
  oneOff: BusyTimeOut[];
  weekly: RecurringBusyTimeOut[];
}) {
  const byMember = new Map<number, MemberBusyTimes>();
  const groupFor = (member: { id: number; name: string }) => {
    const group = byMember.get(member.id) ?? { name: member.name, weekly: [], oneOff: [] };
    byMember.set(member.id, group);
    return group;
  };
  for (const rule of weekly) groupFor(rule.member).weekly.push(rule);
  for (const busyTime of oneOff) groupFor(busyTime.member).oneOff.push(busyTime);
  const groups = [...byMember.values()].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <ul className="space-y-4">
      {groups.map((group) => (
        <li key={group.name}>
          <h3 className="font-semibold">{group.name}</h3>
          <ul className="mt-1 space-y-1">
            {group.weekly.map((rule) => (
              <li key={`weekly-${rule.id}`} className="border-l-2 border-dashed border-ink pl-3">
                <span className="font-medium">Every week:</span> {formatWeeklyTimes(rule)}
                <span className="text-gray-700"> · {formatWeeklyDates(rule)}</span>
              </li>
            ))}
            {group.oneOff.map((busyTime) => (
              <li key={busyTime.id} className="border-l-2 border-dashed border-ink pl-3">
                {formatRange(busyTime.starts_at, busyTime.ends_at)}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

function MoreNote({ page, noun }: { page: { total: number; items: unknown[] }; noun: string }) {
  if (page.total <= page.items.length) return null;
  return (
    <p className="mt-2 text-sm text-gray-700">
      Showing the first {page.items.length} of {page.total} {noun}.
    </p>
  );
}
