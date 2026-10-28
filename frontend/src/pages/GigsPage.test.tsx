import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import {
  asCasey,
  asManager,
  asRiley,
  asSam,
  blueDoor,
  restricted,
  rileyInvitation,
  toListItem,
} from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

const emptyPage = { items: [], total: 0, page: 1, page_size: 100 };

describe("gigs page", () => {
  it("shows a loading message while gigs load", async () => {
    server.use(http.get("*/api/v1/gigs", () => delay("infinite")));

    renderApp("/gigs", { as: asManager });

    expect(await screen.findByRole("status")).toHaveTextContent("Loading gigs…");
  });

  it("shows an error with a retry that works", async () => {
    server.use(
      http.get(
        "*/api/v1/gigs",
        () => HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/gigs", { as: asManager });

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("link", { name: /The Blue Door/ })).toBeInTheDocument();
  });

  it("explains a network failure in plain words", async () => {
    server.use(http.get("*/api/v1/gigs", () => HttpResponse.error()));

    renderApp("/gigs", { as: asSam });

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't reach Roadhouse.");
  });

  it("tells the manager how to start when there are no gigs", async () => {
    server.use(http.get("*/api/v1/gigs", () => HttpResponse.json(emptyPage)));

    renderApp("/gigs", { as: asManager });

    expect(
      await screen.findByText("No gigs yet. Add your first gig to start tracking it."),
    ).toBeInTheDocument();
  });

  it("tells a member when they have no gigs or invitations", async () => {
    server.use(http.get("*/api/v1/gigs", () => HttpResponse.json(emptyPage)));

    renderApp("/gigs", { as: asCasey });

    expect(await screen.findByText("No gigs or invitations yet.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Add gig" })).not.toBeInTheDocument();
  });

  it("offers the band leader the Add gig button", async () => {
    renderApp("/gigs", { as: asSam });

    expect(await screen.findByRole("link", { name: "Add gig" })).toBeInTheDocument();
  });

  it("lists the manager's gigs by date, then the undated drafts", async () => {
    renderApp("/gigs", { as: asManager });

    const byDate = await screen.findByRole("region", { name: "By date" });
    const links = within(byDate).getAllByRole("link");
    expect(links[0]).toHaveTextContent("The Blue Door");
    expect(links[0]).toHaveTextContent("Sun, Oct 18, 2026 · 8:00 PM");
    expect(links[0]).toHaveTextContent("Duo");
    expect(links[0]).toHaveTextContent("Booked");
    expect(links[1]).toHaveTextContent("Hub City Tap");
    expect(links[1]).toHaveTextContent("Pending");

    const undated = screen.getByRole("region", { name: "Undated" });
    expect(within(undated).getByRole("link", { name: /Wedding inquiry/ })).toHaveTextContent(
      "No date yet",
    );
  });

  it("opens a gig when its row is clicked", async () => {
    const { user } = renderApp("/gigs", { as: asManager });

    await user.click(await screen.findByRole("link", { name: /The Blue Door/ }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "The Blue Door" }),
    ).toBeInTheDocument();
  });

  it("flags a member's open invitations", async () => {
    server.use(
      http.get("*/api/v1/gigs", ({ request }) =>
        new URL(request.url).searchParams.get("has_date") === "true"
          ? HttpResponse.json({ ...emptyPage, items: [toListItem(rileyInvitation)], total: 1 })
          : HttpResponse.json(emptyPage),
      ),
    );

    renderApp("/gigs", { as: asRiley });

    expect(await screen.findByRole("link", { name: /Morgan's Pub/ })).toHaveTextContent(
      "Invited: please answer",
    );
  });

  it("shows a member the gigs they're not on as 'Not assigned' rows that don't open", async () => {
    server.use(
      http.get("*/api/v1/gigs", ({ request }) =>
        new URL(request.url).searchParams.get("has_date") === "true"
          ? HttpResponse.json({ ...emptyPage, items: [restricted(blueDoor)], total: 1 })
          : HttpResponse.json(emptyPage),
      ),
    );

    renderApp("/gigs", { as: asRiley });

    const byDate = await screen.findByRole("region", { name: "By date" });
    const row = within(byDate).getByRole("listitem");
    expect(row).toHaveTextContent("Not assigned");
    expect(row).toHaveTextContent("Sun, Oct 18, 2026");
    expect(row).not.toHaveTextContent("The Blue Door");
    expect(within(row).queryByRole("link")).not.toBeInTheDocument();
  });

  it("says when only some gigs are shown", async () => {
    server.use(
      http.get("*/api/v1/gigs", ({ request }) =>
        new URL(request.url).searchParams.get("has_date") === "true"
          ? HttpResponse.json({ ...emptyPage, items: [toListItem(blueDoor)], total: 150 })
          : HttpResponse.json(emptyPage),
      ),
    );

    renderApp("/gigs", { as: asSam });

    expect(await screen.findByText("Showing the first 1 of 150 gigs.")).toBeInTheDocument();
  });
});
