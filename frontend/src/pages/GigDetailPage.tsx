import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useId, useState, type FormEvent, type ReactNode } from "react";
import { Link, useParams } from "react-router";

import { api } from "../api/client";
import { ApiError, errorMessage, unwrap } from "../api/errors";
import type { GigDetail, MemberRead, SlotOut } from "../api/types";
import { TextField } from "../components/GigForm";
import { ErrorMessage, Loading } from "../components/QueryStates";
import {
  CONTACT_LABELS,
  formatDate,
  formatMoney,
  formatTime,
  GIG_STATUS_LABELS,
  LINEUP_SIZE_LABELS,
  ROLE_LABELS,
  SLOT_STATUS_LABELS,
} from "../format";
import { runsTheBand, useActingMember } from "../session";
import { gigQueryKey, useGig, useMembers } from "./gigQueries";

const primaryButton =
  "rounded bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60";
const secondaryButton =
  "rounded border border-gray-500 px-4 py-2 font-medium hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-brand-600 disabled:opacity-60";
const MONEY_PATTERN = /^\d+(\.\d{1,2})?$/;

/** Store a changed gig in the cache and refresh the lists that show it. */
function useGigUpdated(gigId: number) {
  const queryClient = useQueryClient();
  return (updated: GigDetail) => {
    queryClient.setQueryData(gigQueryKey(gigId), updated);
    void queryClient.invalidateQueries({ queryKey: ["gigs"] });
  };
}

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
  const mySlot = gig.slots.find((slot) => slot.id === gig.my_slot_id);

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

      {mySlot && <MyInvitation gig={gig} slot={mySlot} />}

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
              <ScheduleItem label="End" iso={gig.end_at} />
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
          <Detail term="Lineup">
            {gig.lineup_size ? LINEUP_SIZE_LABELS[gig.lineup_size] : "No roles yet"}
          </Detail>
          {runsTheBand(member) && (
            <Detail term="Total pay">
              {gig.pay_cents === null ? notSet : formatMoney(gig.pay_cents)}
            </Detail>
          )}
        </dl>
      </section>

      {/* Venue contacts are private to the manager and band leader. */}
      {runsTheBand(member) && (
        <section aria-labelledby="contacts-heading" className="mt-6">
          <h2 id="contacts-heading" className="text-lg font-semibold">
            Contacts
          </h2>
          {gig.contacts.length === 0 ? (
            <p className="mt-1 text-gray-700">No contacts yet.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {gig.contacts.map((contact) => (
                <li key={contact.id}>
                  <span className="font-medium">{CONTACT_LABELS[contact.label]}:</span>{" "}
                  {[contact.name, contact.phone, contact.email].filter(Boolean).join(" · ")}
                  {contact.notes && <p className="text-sm text-gray-700">{contact.notes}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section aria-labelledby="lineup-heading" className="mt-6">
        <h2 id="lineup-heading" className="text-lg font-semibold">
          Lineup
        </h2>
        {gig.slots.length === 0 ? (
          <p className="mt-1 text-gray-700">
            {member.isManager
              ? "No roles yet. Choose the roles this gig needs under Edit details."
              : "No roles yet."}
          </p>
        ) : member.isManager ? (
          <ManagerLineup gig={gig} />
        ) : (
          <ul className="mt-2 space-y-1">
            {gig.slots.map((slot) => (
              <li key={slot.id}>
                <span className="font-medium">{ROLE_LABELS[slot.role]}:</span>{" "}
                {slot.member && slot.status === "accepted" ? slot.member.name : "Not confirmed yet"}
                {/* The band leader sees everyone's pay. Other members see only their own. */}
                {runsTheBand(member) &&
                  slot.pay_cents !== null &&
                  ` · ${formatMoney(slot.pay_cents)}`}
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

/** A member's own invitation: what they're asked to play, their pay, and accept or decline. */
function MyInvitation({ gig, slot }: { gig: GigDetail; slot: SlotOut }) {
  const onUpdated = useGigUpdated(gig.id);
  const answer = useMutation({
    mutationFn: (choice: "accept" | "decline") =>
      unwrap(
        choice === "accept"
          ? api.POST("/api/v1/gigs/{gig_id}/slots/{slot_id}/accept", {
              params: { path: { gig_id: gig.id, slot_id: slot.id } },
            })
          : api.POST("/api/v1/gigs/{gig_id}/slots/{slot_id}/decline", {
              params: { path: { gig_id: gig.id, slot_id: slot.id } },
            }),
      ),
    onSuccess: onUpdated,
  });

  return (
    <section
      aria-labelledby="invitation-heading"
      className="mt-4 rounded border border-brand-600 bg-brand-50 p-4"
    >
      <h2 id="invitation-heading" className="text-lg font-semibold">
        Your invitation
      </h2>
      <p className="mt-1">
        Role: <strong>{ROLE_LABELS[slot.role]}</strong>
      </p>
      <p>Your pay: {slot.pay_cents === null ? "Not set yet" : formatMoney(slot.pay_cents)}</p>
      <p className="font-medium">{SLOT_STATUS_LABELS[slot.status]}</p>
      {slot.status === "invited" && gig.status === "potential" && (
        <div className="mt-3 flex flex-wrap gap-3">
          <button
            type="button"
            className={primaryButton}
            disabled={answer.isPending}
            onClick={() => answer.mutate("accept")}
          >
            Accept
          </button>
          <button
            type="button"
            className={secondaryButton}
            disabled={answer.isPending}
            onClick={() => answer.mutate("decline")}
          >
            Decline
          </button>
        </div>
      )}
      {answer.isError && (
        <div className="mt-3">
          <ErrorMessage message={errorMessage(answer.error)} />
        </div>
      )}
    </section>
  );
}

function ManagerLineup({ gig }: { gig: GigDetail }) {
  const members = useMembers();

  if (members.isPending) return <Loading label="Loading band members…" />;
  if (members.isError) {
    return (
      <ErrorMessage message={errorMessage(members.error)} onRetry={() => void members.refetch()} />
    );
  }
  const players = members.data.items.filter((candidate) => !candidate.is_manager);

  return (
    <ul className="mt-2 space-y-4">
      {gig.slots.map((slot) => (
        <li key={slot.id} className="rounded border border-gray-200 p-3">
          <h3 className="font-semibold">{ROLE_LABELS[slot.role]}</h3>
          <p>
            {slot.member ? slot.member.name : "Nobody invited yet"}
            {slot.member && ` · ${SLOT_STATUS_LABELS[slot.status]}`}
            {slot.pay_cents !== null && ` · ${formatMoney(slot.pay_cents)}`}
          </p>
          {gig.status === "potential" && slot.status !== "accepted" && (
            <InviteForm gig={gig} slot={slot} players={players} />
          )}
        </li>
      ))}
    </ul>
  );
}

interface InviteFormProps {
  gig: GigDetail;
  slot: SlotOut;
  players: MemberRead[];
}

function InviteForm({ gig, slot, players }: InviteFormProps) {
  const id = useId();
  const roleLabel = ROLE_LABELS[slot.role];
  const [memberId, setMemberId] = useState(slot.member ? String(slot.member.id) : "");
  const [pay, setPay] = useState(slot.pay_cents === null ? "" : (slot.pay_cents / 100).toFixed(2));
  const [payError, setPayError] = useState<string | undefined>();
  const onUpdated = useGigUpdated(gig.id);
  const invite = useMutation({
    mutationFn: (body: { member_id: number; pay_cents: number | null }) =>
      unwrap(
        api.POST("/api/v1/gigs/{gig_id}/slots/{slot_id}/invite", {
          params: { path: { gig_id: gig.id, slot_id: slot.id } },
          body,
        }),
      ),
    onSuccess: onUpdated,
  });

  // Members who usually play this role are listed first; anyone can be asked as a backup.
  const usual = players.filter((player) => player.primary_role === slot.role);
  const others = players.filter((player) => player.primary_role !== slot.role);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pay.trim() && !MONEY_PATTERN.test(pay.trim())) {
      setPayError("Enter pay as a dollar amount, like 150 or 150.50.");
      return;
    }
    setPayError(undefined);
    invite.mutate({
      member_id: Number(memberId),
      pay_cents: pay.trim() ? Math.round(Number(pay.trim()) * 100) : null,
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-2 grid gap-3 sm:grid-cols-3">
      <div>
        <label htmlFor={`${id}-member`} className="block text-sm font-medium">
          Invite for {roleLabel}
        </label>
        <select
          id={`${id}-member`}
          value={memberId}
          onChange={(event) => setMemberId(event.target.value)}
          className="mt-1 w-full rounded border border-gray-400 px-3 py-2 focus-visible:outline-2 focus-visible:outline-brand-600"
        >
          <option value="">Choose a member</option>
          {usual.length > 0 && (
            <optgroup label={`Plays ${roleLabel}`}>
              {usual.map((player) => (
                <option key={player.id} value={String(player.id)}>
                  {player.name}
                </option>
              ))}
            </optgroup>
          )}
          {others.length > 0 && (
            <optgroup label="Backups">
              {others.map((player) => (
                <option key={player.id} value={String(player.id)}>
                  {player.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </div>
      <TextField
        id={`${id}-pay`}
        label={`Pay for ${roleLabel} (USD)`}
        inputMode="decimal"
        value={pay}
        error={payError}
        onChange={setPay}
      />
      <div className="flex items-end">
        <button type="submit" className={primaryButton} disabled={!memberId || invite.isPending}>
          {slot.member ? "Send new invitation" : "Send invitation"}
        </button>
      </div>
      {invite.isError && (
        <div className="sm:col-span-3">
          <ErrorMessage message={errorMessage(invite.error)} />
        </div>
      )}
    </form>
  );
}

function BookingPanel({ gig }: { gig: GigDetail }) {
  const onUpdated = useGigUpdated(gig.id);
  const book = useMutation({
    mutationFn: () =>
      unwrap(api.POST("/api/v1/gigs/{gig_id}/book", { params: { path: { gig_id: gig.id } } })),
    onSuccess: onUpdated,
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
        <p className="mt-1">Everyone has accepted and everything booking needs is filled in.</p>
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
