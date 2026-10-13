import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type { GigListItem, GigPage } from "../api/types";
import { ErrorMessage, Loading } from "../components/QueryStates";
import { formatDate, formatTime, GIG_STATUS_LABELS, LINEUP_SIZE_LABELS } from "../format";
import { useActingMember } from "../session";

const PAGE_SIZE = 100;

export function GigsPage() {
  const member = useActingMember();
  const dated = useQuery({
    queryKey: ["gigs", "dated"],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/gigs", {
          params: { query: { has_date: true, sort: "first_set_at", page_size: PAGE_SIZE } },
        }),
      ),
  });
  // Drafts without a date yet. Members see the ones they've been invited to.
  const undated = useQuery({
    queryKey: ["gigs", "undated"],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/gigs", {
          params: { query: { has_date: false, sort: "-created_at", page_size: PAGE_SIZE } },
        }),
      ),
  });

  const queries = [dated, undated];
  const failed = queries.find((query) => query.isError);

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Gigs</h1>
        {member.isManager && (
          <Link
            to="/gigs/new"
            className="rounded bg-brand-700 px-4 py-2 font-medium text-white hover:bg-brand-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
          >
            Add gig
          </Link>
        )}
      </div>

      <div className="mt-4">
        {failed ? (
          <ErrorMessage
            message={errorMessage(failed.error)}
            onRetry={() => queries.forEach((query) => void query.refetch())}
          />
        ) : queries.some((query) => query.isPending) ? (
          <Loading label="Loading gigs…" />
        ) : (
          <GigLists dated={dated.data} undated={undated.data} isManager={member.isManager} />
        )}
      </div>
    </section>
  );
}

interface GigListsProps {
  dated: GigPage | undefined;
  undated: GigPage | undefined;
  isManager: boolean;
}

function GigLists({ dated, undated, isManager }: GigListsProps) {
  const datedItems = dated?.items ?? [];
  const undatedItems = undated?.items ?? [];

  if (datedItems.length === 0 && undatedItems.length === 0) {
    return (
      <p className="text-gray-700">
        {isManager
          ? "No gigs yet. Add your first gig to start tracking it."
          : "No gigs or invitations yet."}
      </p>
    );
  }

  return (
    <div className="space-y-8">
      {datedItems.length > 0 && <GigSection title="By date" page={dated} items={datedItems} />}
      {undatedItems.length > 0 && (
        <GigSection title="Undated" page={undated} items={undatedItems} />
      )}
    </div>
  );
}

interface GigSectionProps {
  title: string;
  page: GigPage | undefined;
  items: GigListItem[];
}

function GigSection({ title, page, items }: GigSectionProps) {
  const headingId = `gigs-${title.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <section aria-labelledby={headingId}>
      <h2 id={headingId} className="text-lg font-semibold">
        {title}
      </h2>
      <ul className="mt-2 space-y-2">
        {items.map((gig) => (
          <GigRow key={gig.id} gig={gig} />
        ))}
      </ul>
      {page && page.total > items.length && (
        <p className="mt-2 text-sm text-gray-700">
          Showing the first {items.length} of {page.total} gigs.
        </p>
      )}
    </section>
  );
}

function GigRow({ gig }: { gig: GigListItem }) {
  const when = gig.first_set_at
    ? `${formatDate(gig.first_set_at)} · ${formatTime(gig.first_set_at)}`
    : "No date yet";

  if (gig.restricted) {
    // A gig this member isn't on: only the date, with "Not assigned" as the main text.
    // It is deliberately not a link, so nothing opens on click or Enter.
    return (
      <li className="rounded border border-gray-200 bg-gray-100 px-4 py-3 text-gray-600">
        <p className="font-semibold">Not assigned</p>
        <p className="text-sm">{gig.first_set_at ? formatDate(gig.first_set_at) : when}</p>
      </li>
    );
  }

  return (
    <li>
      <Link
        to={`/gigs/${gig.id}`}
        className="block rounded border border-gray-300 px-4 py-3 hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600"
      >
        <span className="block font-semibold">{gig.venue_name ?? "Untitled gig"}</span>
        <span className="block text-sm text-gray-700">{when}</span>
        <span className="mt-1 flex gap-3 text-sm">
          <span>{gig.lineup_size ? LINEUP_SIZE_LABELS[gig.lineup_size] : "No roles yet"}</span>
          <span className="font-medium">{GIG_STATUS_LABELS[gig.status]}</span>
          {gig.my_slot_status === "invited" && (
            <span className="rounded bg-brand-50 px-2 font-semibold">Invited: please answer</span>
          )}
          {gig.my_slot_status === "accepted" && gig.status === "potential" && (
            <span>You accepted</span>
          )}
        </span>
      </Link>
    </li>
  );
}
