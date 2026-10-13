import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router";

import { api } from "../api/client";
import { ApiError, errorMessage, unwrap } from "../api/errors";
import type { GigDetail, LineupAssignmentIn } from "../api/types";
import { ErrorMessage, Loading } from "../components/QueryStates";
import {
  formatDate,
  formatMoney,
  formatTime,
  GIG_STATUS_LABELS,
  GIG_TYPE_LABELS,
  ROLE_LABELS,
} from "../format";
import { useActingMember } from "../session";
import { gigQueryKey, useGig, useMembers } from "./gigQueries";

const primaryButton =
  "rounded bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60";

export function GigDetailPage() {
  const gigId = Number(useParams().gigId);
  const gig = useGig(gigId);

  return (
    <section>
      <Link to="/gigs" className="text-sm text-brand-700 underline">
        Back to gigs
      </Link>
      <div className="mt-2">
        {gig.isPending && <Loading label="Loading the gig…" />}
        {gig.isError && <GigLoadError error={gig.error} onRetry={() => void gig.refetch()} />}
        {gig.isSuccess && <GigDetails gig={gig.data} />}
      </div>
    </section>
  );
}

function GigLoadError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
    return (
      <div>
        <h1 className="text-2xl font-bold">
          {error.status === 404 ? "Gig not found" : "Not your gig"}
        </h1>
        <p className="mt-2 text-gray-700">{error.message}</p>
      </div>
    );
  }
  return <ErrorMessage message={errorMessage(error)} onRetry={onRetry} />;
}

function GigDetails({ gig }: { gig: GigDetail }) {
  const member = useActingMember();
  const notSet = <span className="text-gray-600">Not set</span>;

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">{gig.venue_name ?? "Untitled gig"}</h1>
        <span className="rounded border border-gray-400 px-2 py-0.5 text-sm font-medium">
          {GIG_STATUS_LABELS[gig.status]}
        </span>
        {member.isManager && (
          <Link to={`/gigs/${gig.id}/edit`} className="text-brand-700 underline">
            Edit details
          </Link>
        )}
      </div>

      <section aria-labelledby="schedule-heading" className="mt-6">
        <h2 id="schedule-heading" className="text-lg font-semibold">
          Schedule
        </h2>
        {gig.first_set_at ? (
          <>
            <p className="mt-1">{formatDate(gig.first_set_at)}</p>
            <ol className="mt-2 space-y-1">
              <ScheduleItem label="Load-in" iso={gig.load_in_at} />
              <ScheduleItem label="Soundcheck" iso={gig.soundcheck_at} />
              <ScheduleItem label="First set" iso={gig.first_set_at} />
            </ol>
          </>
        ) : (
          <p className="mt-1 text-gray-700">No date or time yet.</p>
        )}
      </section>

      <section aria-labelledby="details-heading" className="mt-6">
        <h2 id="details-heading" className="text-lg font-semibold">
          Details
        </h2>
        <dl className="mt-2 grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
          <Detail term="Venue address">{gig.venue_address ?? notSet}</Detail>
          <Detail term="Gig type">{gig.gig_type ? GIG_TYPE_LABELS[gig.gig_type] : notSet}</Detail>
          {member.isManager && (
            <Detail term="Pay">
              {gig.pay_cents === null ? notSet : formatMoney(gig.pay_cents)}
            </Detail>
          )}
          <Detail term="Venue contact">
            <ContactText contact={gig.venue_contact} />
          </Detail>
          <Detail term="Booking contact">
            <ContactText contact={gig.booking_contact} />
          </Detail>
        </dl>
      </section>

      <section aria-labelledby="lineup-heading" className="mt-6">
        <h2 id="lineup-heading" className="text-lg font-semibold">
          Lineup
        </h2>
        {gig.lineup.length === 0 ? (
          <p className="mt-1 text-gray-700">Choose a gig type to set the lineup.</p>
        ) : member.isManager ? (
          <LineupEditor key={gig.lineup.map((slot) => slot.slot).join()} gig={gig} />
        ) : (
          <ul className="mt-2 space-y-1">
            {gig.lineup.map((slot) => (
              <li key={slot.slot}>
                <span className="font-medium">{ROLE_LABELS[slot.slot]}:</span>{" "}
                {slot.member ? slot.member.name : "Open"}
              </li>
            ))}
          </ul>
        )}
      </section>

      {member.isManager && gig.status === "potential" && <BookingPanel gig={gig} />}
    </>
  );
}

function ScheduleItem({ label, iso }: { label: string; iso: string | null }) {
  return (
    <li>
      <span className="inline-block w-28 font-medium">{label}</span>
      {iso ? formatTime(iso) : "Not set"}
    </li>
  );
}

function Detail({ term, children }: { term: string; children: ReactNode }) {
  return (
    <>
      <dt className="font-medium">{term}</dt>
      <dd>{children}</dd>
    </>
  );
}

function ContactText({ contact }: { contact: GigDetail["venue_contact"] }) {
  if (!contact) return <span className="text-gray-600">Not set</span>;
  const parts = [contact.name, contact.phone, contact.email].filter(Boolean);
  return <span>{parts.join(" · ")}</span>;
}

function LineupEditor({ gig }: { gig: GigDetail }) {
  const queryClient = useQueryClient();
  const members = useMembers();
  const [choices, setChoices] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      gig.lineup.map((slot) => [slot.slot, slot.member ? String(slot.member.id) : ""]),
    ),
  );
  const save = useMutation({
    mutationFn: (lineup: LineupAssignmentIn[]) =>
      unwrap(
        api.PATCH("/api/v1/gigs/{gig_id}", {
          params: { path: { gig_id: gig.id } },
          body: { lineup },
        }),
      ),
    onSuccess: (updated) => {
      queryClient.setQueryData(gigQueryKey(gig.id), updated);
      void queryClient.invalidateQueries({ queryKey: ["gigs"] });
    },
  });

  if (members.isPending) return <Loading label="Loading band members…" />;
  if (members.isError) {
    return (
      <ErrorMessage message={errorMessage(members.error)} onRetry={() => void members.refetch()} />
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const lineup = gig.lineup
      .filter((slot) => choices[slot.slot])
      .map((slot) => ({ slot: slot.slot, member_id: Number(choices[slot.slot]) }));
    save.mutate(lineup);
  }

  return (
    <form onSubmit={handleSubmit} className="mt-2 max-w-md space-y-3">
      {gig.lineup.map((slot) => {
        const id = `lineup-${slot.slot}`;
        const eligible = members.data.items.filter(
          (candidate) => !candidate.is_manager && candidate.primary_role === slot.slot,
        );
        return (
          <div key={slot.slot}>
            <label htmlFor={id} className="block font-medium">
              {ROLE_LABELS[slot.slot]}
            </label>
            <select
              id={id}
              value={choices[slot.slot] ?? ""}
              onChange={(event) =>
                setChoices((previous) => ({ ...previous, [slot.slot]: event.target.value }))
              }
              className="mt-1 w-full rounded border border-gray-400 px-3 py-2 focus-visible:outline-2 focus-visible:outline-brand-600"
            >
              <option value="">Open</option>
              {eligible.map((candidate) => (
                <option key={candidate.id} value={String(candidate.id)}>
                  {candidate.name}
                </option>
              ))}
            </select>
          </div>
        );
      })}
      {save.isError && <ErrorMessage message={errorMessage(save.error)} />}
      {save.isSuccess && (
        <p role="status" className="text-green-900">
          Lineup saved.
        </p>
      )}
      <button type="submit" disabled={save.isPending} className={primaryButton}>
        {save.isPending ? "Saving…" : "Save lineup"}
      </button>
    </form>
  );
}

function BookingPanel({ gig }: { gig: GigDetail }) {
  const queryClient = useQueryClient();
  const book = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/v1/gigs/{gig_id}/book", { params: { path: { gig_id: gig.id } } })),
    onSuccess: (updated) => {
      queryClient.setQueryData(gigQueryKey(gig.id), updated);
      void queryClient.invalidateQueries({ queryKey: ["gigs"] });
    },
  });

  return (
    <section aria-labelledby="booking-heading" className="mt-8 rounded border border-gray-300 p-4">
      <h2 id="booking-heading" className="text-lg font-semibold">
        Booking
      </h2>
      {gig.missing_for_booking.length > 0 ? (
        <>
          <p className="mt-1">Still needed before this gig can be booked:</p>
          <ul className="mt-1 list-disc pl-6">
            {gig.missing_for_booking.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-1">Everything booking needs is filled in.</p>
      )}
      {book.isError && (
        <div className="mt-3">
          <ErrorMessage message={errorMessage(book.error)} />
        </div>
      )}
      <button
        type="button"
        onClick={() => book.mutate()}
        disabled={book.isPending}
        className={`${primaryButton} mt-3`}
      >
        {book.isPending ? "Booking…" : "Book gig"}
      </button>
    </section>
  );
}
