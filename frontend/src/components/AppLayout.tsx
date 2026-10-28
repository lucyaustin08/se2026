import { useQueryClient } from "@tanstack/react-query";
import { Navigate, NavLink, Outlet, useNavigate } from "react-router";

import { NAV_ITEMS } from "../navigation";
import { useSession } from "../session";

export function AppLayout() {
  const { member, signOut } = useSession();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  if (!member) {
    return <Navigate to="/login" replace />;
  }

  function switchUser() {
    signOut();
    // Cached answers belong to the previous user, so drop them.
    queryClient.clear();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-paper font-sans text-ink">
      <header className="border-b border-gray-300">
        <div className="mx-auto max-w-5xl px-4 py-3">
          {/* Anton has one weight, so no font-bold here: the browser would fake it. */}
          <p className="font-display text-3xl leading-tight tracking-wide text-brand-700 uppercase">
            Roadhouse
          </p>
          <nav aria-label="Main" className="mt-2 overflow-x-auto">
            <ul className="flex gap-1 whitespace-nowrap">
              {NAV_ITEMS.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    end={item.path === "/"}
                    className={({ isActive }) =>
                      [
                        "inline-block px-3 py-2 text-sm",
                        // Inset so the nav's horizontal scroll doesn't clip the outline.
                        "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-600",
                        // Active state is shown by weight and underline, not color alone.
                        isActive
                          ? "bg-brand-50 font-semibold underline underline-offset-4"
                          : "hover:bg-gray-100",
                      ].join(" ")
                    }
                  >
                    {item.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-700">
            <p>
              Using Roadhouse as <strong>{member.name}</strong> (
              {member.isManager ? "band manager" : "band member"})
            </p>
            <button
              type="button"
              onClick={switchUser}
              className="border border-gray-400 px-2 py-1 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-brand-600"
            >
              Switch user
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
