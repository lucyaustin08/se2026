import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type { GigUpdate } from "../api/types";
import { GigForm, gigToFormValues } from "../components/GigForm";
import { ErrorMessage, Loading } from "../components/QueryStates";
import { runsTheBand, useActingMember } from "../session";
import { gigQueryKey, useGig } from "./gigQueries";
import { ManagerOnly } from "./NewGigPage";

export function EditGigPage() {
  const member = useActingMember();
  const gigId = Number(useParams().gigId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const gig = useGig(gigId);
  const save = useMutation({
    mutationFn: (body: GigUpdate) =>
      unwrap(api.PATCH("/api/v1/gigs/{gig_id}", { params: { path: { gig_id: gigId } }, body })),
    onSuccess: (updated) => {
      queryClient.setQueryData(gigQueryKey(gigId), updated);
      void queryClient.invalidateQueries({ queryKey: ["gigs"] });
      navigate(`/gigs/${gigId}`);
    },
  });

  if (!runsTheBand(member)) {
    return <ManagerOnly action="edit gigs" />;
  }

  return (
    <section>
      <Link to={`/gigs/${gigId}`} className="text-sm text-brand-700 underline">
        Back to the gig
      </Link>
      <h1 className="mt-2 text-2xl font-bold">Edit gig</h1>
      <div className="mt-6">
        {gig.isPending && <Loading label="Loading the gig…" />}
        {gig.isError && (
          <ErrorMessage message={errorMessage(gig.error)} onRetry={() => void gig.refetch()} />
        )}
        {gig.isSuccess && (
          <GigForm
            initialValues={gigToFormValues(gig.data)}
            submitLabel="Save changes"
            pending={save.isPending}
            serverError={save.isError ? errorMessage(save.error) : null}
            onSubmit={(body) => save.mutate(body)}
          />
        )}
      </div>
    </section>
  );
}
