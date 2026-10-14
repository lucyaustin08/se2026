import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { errorMessage, unwrap } from "../api/errors";
import type { MemberRead } from "../api/types";
import { ErrorMessage, Loading } from "../components/QueryStates";
import { ROLE_LABELS } from "../format";
import { useSession } from "../session";

const choiceButton =
  "w-full rounded border border-gray-300 px-4 py-3 text-left hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-brand-600";

export function LoginPage() {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const members = useQuery({
    queryKey: ["members"],
    queryFn: () => unwrap(api.GET("/api/v1/members", { params: { query: { page_size: 100 } } })),
  });

  function choose(member: MemberRead) {
    signIn({ id: member.id, name: member.name, isManager: member.is_manager });
    navigate("/gigs");
  }

  return (
    <main className="mx-auto max-w-md px-4 py-10 font-sans text-ink-900">
      <h1 className="text-2xl font-bold text-brand-700">Roadhouse</h1>
      <p className="mt-2 text-gray-700">
        Choose who you are. Real sign-in with your email and password comes in a later sprint.
      </p>

      <div className="mt-6">
        {members.isPending && <Loading label="Loading the band…" />}
        {members.isError && (
          <ErrorMessage
            message={errorMessage(members.error)}
            onRetry={() => void members.refetch()}
          />
        )}
        {members.isSuccess && <MemberChoices members={members.data.items} onChoose={choose} />}
      </div>
    </main>
  );
}

interface MemberChoicesProps {
  members: MemberRead[];
  onChoose: (member: MemberRead) => void;
}

function MemberChoices({ members, onChoose }: MemberChoicesProps) {
  if (members.length === 0) {
    return <p>No band members have been added yet.</p>;
  }
  const manager = members.find((member) => member.is_manager);
  const bandMembers = members.filter((member) => !member.is_manager);

  return (
    <>
      <section aria-labelledby="manager-heading">
        <h2 id="manager-heading" className="text-lg font-semibold">
          Band manager
        </h2>
        {manager ? (
          <button
            type="button"
            className={`${choiceButton} mt-2`}
            onClick={() => onChoose(manager)}
          >
            <span className="block font-semibold">Continue as manager</span>
            <span className="block text-sm text-gray-700">{manager.name}</span>
          </button>
        ) : (
          <p className="mt-2 text-gray-700">No manager has been set up yet.</p>
        )}
      </section>

      <section aria-labelledby="member-heading" className="mt-6">
        <h2 id="member-heading" className="text-lg font-semibold">
          Continue as a member
        </h2>
        {bandMembers.length === 0 ? (
          <p className="mt-2 text-gray-700">No band members have been added yet.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {bandMembers.map((member) => (
              <li key={member.id}>
                <button type="button" className={choiceButton} onClick={() => onChoose(member)}>
                  <span className="block font-semibold">{member.name}</span>
                  <span className="block text-sm text-gray-700">
                    {member.primary_role ? ROLE_LABELS[member.primary_role] : "No role set"}
                    {member.is_band_leader && " · Band leader"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
