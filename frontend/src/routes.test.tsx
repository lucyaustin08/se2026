import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";

import { routes } from "./routes";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
}

function mainNav() {
  return screen.getByRole("navigation", { name: "Main" });
}

describe("app navigation", () => {
  it("lists every section in the main navigation", () => {
    renderAt("/");

    const links = within(mainNav()).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Dashboard",
      "Gigs",
      "Scheduling",
      "Songs & Setlists",
      "Members",
      "Booking",
    ]);
  });

  it("opens on the dashboard and marks it as the current page", () => {
    renderAt("/");

    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
    expect(within(mainNav()).getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("moves to a section when its link is clicked", async () => {
    const user = userEvent.setup();
    renderAt("/");

    await user.click(within(mainNav()).getByRole("link", { name: "Gigs" }));

    expect(screen.getByRole("heading", { level: 1, name: "Gigs" })).toBeInTheDocument();
    expect(within(mainNav()).getByRole("link", { name: "Gigs" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(mainNav()).getByRole("link", { name: "Dashboard" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("can be operated from the keyboard", async () => {
    const user = userEvent.setup();
    renderAt("/");

    await user.tab();
    await user.tab();
    expect(within(mainNav()).getByRole("link", { name: "Gigs" })).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { level: 1, name: "Gigs" })).toBeInTheDocument();
  });

  it("shows a not-found page with a way back for unknown addresses", async () => {
    const user = userEvent.setup();
    renderAt("/no-such-page");

    expect(screen.getByRole("heading", { level: 1, name: "Page not found" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Go to the dashboard" }));
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
  });
});
