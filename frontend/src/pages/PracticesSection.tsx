import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import { ApiError, errorMessage, unwrap } from "../api/errors";
import type { InvitationStatus, PracticeCreate, PracticeOut } from "../api/types";
import { Dialog } from "../components/Dialog";
import { PracticeForm, type PracticeConflict } from "../components/PracticeForm";
import { ErrorMessage, Loading } from "../components/QueryStates";
import { primaryButton, secondaryButton, sectionHeading } from "../components/ui";
import { formatRange } from "../format";
import { runsTheBand, useActingMember } from "../session";
import { useMembers } from "./gigQueries";

export const PRACTICES_KEY = ["practices"] as const;

export const INVITATION_LABELS: Record<InvitationStatus, string> = {
  invited: "Invited",
  accepted: "Coming",
  declined: "Can't make it",
};

/** Status marks per DESIGN.md: a word plus a line style, so they read without color. */
const INVITATION_MARKS: Record<InvitationStatus, string> = {
  invited: "border border-dashed border-ink",
  accepted: "border-2 border-brand-700",
  declined: "border border-gray-600 text-gray-600 line-through",
};

export function InvitationMark({ status }: { status: InvitationStatus }) {
  return (
    <span className={`inline-block px-1.5 text-sm font-medium ${INVITATION_MARKS[status]}`}>
      {INVITATION_LABELS[status]}
    </span>
  );
}

export function usePractices(startsAfter: string, startsBefore?: string) {
  return useQuery({
    queryKey: [...PRACTICES_KEY, startsAfter, startsBefore ?? "later"],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/practices", {
          params: {
            query: {
              starts_after: startsAfter,
              page_size: 100,
              ...(startsBefore ? { starts_before: startsBefore } : {}),
            },
          },
        }),
      ),
  });
}

export function PracticesSection({ now }: { now: string }) {
  const member = useActingMember();
  const practices = usePractices(now);
  const [scheduling, setScheduling] = useState(false);

  return (
    <section aria-labelledby="practices-heading" className="mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="practices-heading" className={sectionHeading}>
          Upcoming practices
        </h2>
        {runsTheBand(member) && (
          <button type="button" className={primaryButton} onClick={() => setScheduling(true)}>
            Schedule practice
          </button>
        )}
      </div>
      <div className="mt-3">
        {practices.isPending && <Loading label="Loading practices…" />}
        {practices.isError && (
          <ErrorMessage
            message={errorMessage(practices.error)}
            onRetry={() => void practices.refetch()}
          />
        )}
        {practices.isSuccess &&
          (practices.data.items.length === 0 ? (
            <p className="text-gray-700">
              {runsTheBand(member)
                ? "No practices scheduled yet."
                : "You haven't been invited to any upcoming practices."}
            </p>
          ) : (
            <ul className="space-y-3">
              {practices.data.items.map((practice) => (
                <PracticeCard key={practice.id} practice={practice} />
              ))}
            </ul>
          ))}
      </div>
      {scheduling && <ScheduleDialog onClose={() => setScheduling(false)} />}
    </section>
  );
}

export function PracticeCard({ practice }: { practice: PracticeOut }) {
  const member = useActingMember();
  const queryClient = useQueryClient();
  const answer = useMutation({
    mutationFn: (choice: "accept" | "decline") => {
      const params = { path: { practice_id: practice.id } };
      return unwrap(
        choice === "accept"
          ? api.POST("/api/v1/practices/{practice_id}/accept", { params })
          : api.POST("/api/v1/practices/{practice_id}/decline", { params }),
      );
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PRACTICES_KEY }),
  });
  const seesEveryone = runsTheBand(member);

  return (
    <li className="border border-gray-300 bg-paper px-4 py-3">
      <p className="font-semibold">
        Practice · {formatRange(practice.starts_at, practice.ends_at)}
      </p>
      {(practice.location || practice.notes) && (
        <p className="text-sm text-gray-700">
          {[practice.location, practice.notes].filter(Boolean).join(" · ")}
        </p>
      )}
      {practice.my_status && (
        <p className="mt-2 flex flex-wrap items-center gap-2">
          <span className="text-sm">Your answer:</span>
          <InvitationMark status={practice.my_status} />
        </p>
      )}
      {practice.my_status === "invited" && (
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            className={primaryButton}
            disabled={answer.isPending}
            onClick={() => answer.mutate("accept")}
          >
            I'll be there
          </button>
          <button
            type="button"
            className={secondaryButton}
            disabled={answer.isPending}
            onClick={() => answer.mutate("decline")}
          >
            Can't make it
          </button>
        </div>
      )}
      {answer.isError && (
        <div className="mt-2">
          <ErrorMessage message={errorMessage(answer.error)} />
        </div>
      )}
      {seesEveryone && (
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Who's invited">
          {practice.invitations.map((invitation) => (
            <li key={invitation.member.id} className="flex items-center gap-1">
              {invitation.member.name} <InvitationMark status={invitation.status} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function ScheduleDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const members = useMembers();
  const [conflict, setConflict] = useState<PracticeConflict>(null);
  const schedule = useMutation({
    mutationFn: (body: PracticeCreate) => unwrap(api.POST("/api/v1/practices", { body })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRACTICES_KEY });
      onClose();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "practice_overlaps_gig") {
        setConflict({ kind: "overlap", message: error.message });
      } else if (error instanceof ApiError && error.code === "practice_same_day_as_gig") {
        setConflict({ kind: "same_day", message: error.message });
      }
    },
  });
  const conflictCodes = ["practice_overlaps_gig", "practice_same_day_as_gig"];
  const otherError =
    schedule.isError &&
    !(schedule.error instanceof ApiError && conflictCodes.includes(schedule.error.code));

  return (
    <Dialog title="Schedule practice" onClose={onClose}>
      {members.isPending && <Loading label="Loading the band…" />}
      {members.isError && (
        <ErrorMessage
          message={errorMessage(members.error)}
          onRetry={() => void members.refetch()}
        />
      )}
      {members.isSuccess && (
        <PracticeForm
          players={members.data.items.filter((candidate) => !candidate.is_manager)}
          saving={schedule.isPending}
          conflict={conflict}
          saveError={otherError ? errorMessage(schedule.error) : null}
          onSave={(body) => schedule.mutate(body)}
          onCancel={onClose}
          onEdit={() => setConflict(null)}
        />
      )}
    </Dialog>
  );
}
