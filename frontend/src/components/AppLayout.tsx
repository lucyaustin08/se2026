import { NavLink, Outlet } from "react-router";

import { NAV_ITEMS } from "../navigation";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-white font-sans text-ink-900">
      <header className="border-b border-gray-200">
        <div className="mx-auto max-w-5xl px-4 py-3">
          <p className="text-lg font-bold text-brand-700">Roadhouse</p>
          <nav aria-label="Main" className="mt-2 overflow-x-auto">
            <ul className="flex gap-1 whitespace-nowrap">
              {NAV_ITEMS.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    end={item.path === "/"}
                    className={({ isActive }) =>
                      [
                        "inline-block rounded px-3 py-2 text-sm",
                        "focus-visible:outline-2 focus-visible:outline-brand-600",
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
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
