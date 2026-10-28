import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type { GigCreate } from "../api/types";
import { GigForm } from "../components/GigForm";
import { runsTheBand, useActingMember } from "../session";

export function NewGigPage() {
  const member = useActingMember();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const create = useMutation({
    mutationFn: (body: GigCreate) => unwrap(api.POST("/api/v1/gigs", { body })),
    onSuccess: (gig) => {
      queryClient.setQueryData(["gig", gig.id], gig);
      void queryClient.invalidateQueries({ queryKey: ["gigs"] });
      navigate(`/gigs/${gig.id}`);
    },
  });

  if (!runsTheBand(member)) {
    return <ManagerOnly action="add gigs" />;
  }

  return (
    <section>
      <Link to="/gigs" className="text-sm text-brand-700 underline">
        Back to gigs
      </Link>
      <h1 className="mt-2 text-2xl font-bold">Add a gig</h1>
      <p className="mt-1 text-gray-700">It's saved as a potential gig. You can book it later.</p>
      <div className="mt-6">
        <GigForm
          submitLabel="Save gig"
          pending={create.isPending}
          serverError={create.isError ? errorMessage(create.error) : null}
          onSubmit={(body) => create.mutate(body)}
        />
      </div>
    </section>
  );
}

export function ManagerOnly({ action }: { action: string }) {
  return (
    <section>
      <h1 className="text-2xl font-bold">Manager or band leader only</h1>
      <p className="mt-2 text-gray-700">Only the band manager or band leader can {action}.</p>
      <Link to="/gigs" className="mt-4 inline-block text-brand-700 underline">
        Back to gigs
      </Link>
    </section>
  );
}
