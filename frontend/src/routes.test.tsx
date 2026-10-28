import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { asManager } from "./test/fixtures";
import { renderApp } from "./test/render";

function mainNav() {
  return screen.getByRole("navigation", { name: "Main" });
}

describe("app navigation", () => {
  it("sends someone who hasn't chosen who they are to the login page", async () => {
    renderApp("/gigs");

    expect(await screen.findByRole("heading", { level: 1, name: "Roadhouse" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Main" })).not.toBeInTheDocument();
  });

  it("lists every section in the main navigation", () => {
    renderApp("/", { as: asManager });

    const links = within(mainNav()).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "Dashboard",
      "Gigs",
      "Scheduling",
      "Songs & Setlists",
      "Members",
      "Booking",
      "Profile",
    ]);
  });

  it("opens on the dashboard and marks it as the current page", () => {
    renderApp("/", { as: asManager });

    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
    expect(within(mainNav()).getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("moves to a section when its link is clicked", async () => {
    const { user } = renderApp("/", { as: asManager });

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
    const { user } = renderApp("/", { as: asManager });

    await user.tab();
    await user.tab();
    expect(within(mainNav()).getByRole("link", { name: "Gigs" })).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { level: 1, name: "Gigs" })).toBeInTheDocument();
  });

  it("shows who is using the app and lets them switch", async () => {
    const { user } = renderApp("/", { as: asManager });

    expect(screen.getByText(/Using Roadhouse as/)).toHaveTextContent(
      "Using Roadhouse as Jordan Avery (band manager)",
    );

    await user.click(screen.getByRole("button", { name: "Switch user" }));

    expect(await screen.findByRole("button", { name: /Continue as manager/ })).toBeInTheDocument();
  });

  it("shows a not-found page with a way back for unknown addresses", async () => {
    const { user } = renderApp("/no-such-page", { as: asManager });

    expect(screen.getByRole("heading", { level: 1, name: "Page not found" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Go to the dashboard" }));
    expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
  });
});
