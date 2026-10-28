import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type { BusyTimeIn, BusyTimeOut, BusyTimePage } from "../api/types";
import { BusyTimeForm } from "../components/BusyTimeForm";
import { Dialog } from "../components/Dialog";
import { ErrorMessage, Loading } from "../components/QueryStates";
import { pageHeading, primaryButton, secondaryButton, sectionHeading } from "../components/ui";
import { formatRange } from "../format";
import { runsTheBand, useActingMember } from "../session";

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
        Mark when you can't play. Anyone without busy times counts as available.
      </p>
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

type Editing = { kind: "add" } | { kind: "change"; busyTime: BusyTimeOut } | null;

function MyBusyTimes({ now }: { now: string }) {
  const member = useActingMember();
  const busyTimes = useBusyTimes(now, member.id);
  const [editing, setEditing] = useState<Editing>(null);

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
        {busyTimes.isPending && <Loading label="Loading your busy times…" />}
        {busyTimes.isError && (
          <ErrorMessage
            message={errorMessage(busyTimes.error)}
            onRetry={() => void busyTimes.refetch()}
          />
        )}
        {busyTimes.isSuccess &&
          (busyTimes.data.items.length === 0 ? (
            <p className="text-gray-700">
              You haven't marked any busy times, so you count as available.
            </p>
          ) : (
            <>
              <ul className="space-y-2">
                {busyTimes.data.items.map((busyTime) => (
                  <MyBusyTimeRow
                    key={busyTime.id}
                    busyTime={busyTime}
                    onChange={() => setEditing({ kind: "change", busyTime })}
                  />
                ))}
              </ul>
              <MoreNote page={busyTimes.data} />
            </>
          ))}
      </div>
      {editing && <BusyTimeDialog editing={editing} onClose={() => setEditing(null)} />}
    </section>
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
    <li className="flex flex-wrap items-center justify-between gap-3 border border-gray-300 bg-paper px-4 py-3">
      <span>
        <span className="mr-2 inline-block border border-dashed border-ink px-1.5 text-sm font-medium">
          Busy
        </span>
        {range}
      </span>
      <span className="flex gap-2">
        <button
          type="button"
          className={secondaryButton}
          onClick={onChange}
          aria-label={`Change busy time ${range}`}
        >
          Change
        </button>
        <button
          type="button"
          className={secondaryButton}
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
          aria-label={`Delete busy time ${range}`}
        >
          Delete
        </button>
      </span>
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
  const save = useMutation({
    mutationFn: (body: BusyTimeIn) =>
      editing.kind === "add"
        ? unwrap(api.POST("/api/v1/busy-times", { body }))
        : unwrap(
            api.PATCH("/api/v1/busy-times/{busy_time_id}", {
              params: { path: { busy_time_id: editing.busyTime.id } },
              body,
            }),
          ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: BUSY_TIMES_KEY });
      onClose();
    },
  });

  return (
    <Dialog title={editing.kind === "add" ? "Add busy time" : "Change busy time"} onClose={onClose}>
      <p className="mb-4 text-sm text-gray-700">
        A one-off stretch of time you can't play. It can run over several days.
      </p>
      <BusyTimeForm
        initial={editing.kind === "change" ? editing.busyTime : undefined}
        submitLabel={editing.kind === "add" ? "Add busy time" : "Save changes"}
        saving={save.isPending}
        saveError={save.isError ? errorMessage(save.error) : null}
        onSave={(body) => save.mutate(body)}
        onCancel={onClose}
      />
    </Dialog>
  );
}

function BandBusyTimes({ now }: { now: string }) {
  const busyTimes = useBusyTimes(now);

  return (
    <section aria-labelledby="band-heading" className="mt-8">
      <h2 id="band-heading" className={sectionHeading}>
        Everyone's busy times
      </h2>
      <p className="mt-1 text-sm text-gray-700">Only the manager and band leader see these.</p>
      <div className="mt-3">
        {busyTimes.isPending && <Loading label="Loading the band's busy times…" />}
        {busyTimes.isError && (
          <ErrorMessage
            message={errorMessage(busyTimes.error)}
            onRetry={() => void busyTimes.refetch()}
          />
        )}
        {busyTimes.isSuccess &&
          (busyTimes.data.items.length === 0 ? (
            <p className="text-gray-700">
              Nobody has marked any busy times. Everyone is available.
            </p>
          ) : (
            <>
              <BusyTimesByMember items={busyTimes.data.items} />
              <MoreNote page={busyTimes.data} />
            </>
          ))}
      </div>
    </section>
  );
}

function BusyTimesByMember({ items }: { items: BusyTimeOut[] }) {
  const byMember = new Map<number, { name: string; ranges: BusyTimeOut[] }>();
  for (const item of items) {
    const group = byMember.get(item.member.id) ?? { name: item.member.name, ranges: [] };
    group.ranges.push(item);
    byMember.set(item.member.id, group);
  }
  const groups = [...byMember.values()].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <ul className="space-y-4">
      {groups.map((group) => (
        <li key={group.name}>
          <h3 className="font-semibold">{group.name}</h3>
          <ul className="mt-1 space-y-1">
            {group.ranges.map((busyTime) => (
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

function MoreNote({ page }: { page: BusyTimePage }) {
  if (page.total <= page.items.length) return null;
  return (
    <p className="mt-2 text-sm text-gray-700">
      Showing the first {page.items.length} of {page.total} busy times.
    </p>
  );
}
