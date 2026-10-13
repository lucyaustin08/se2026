import { screen } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { GigUpdate } from "../api/types";
import { asManager, asSam, blueDoor } from "../test/fixtures";
import { errorBody, saveGig } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("edit gig page", () => {
  it("shows a loading message while the gig loads", async () => {
    server.use(http.get("*/api/v1/gigs/:gigId", () => delay("infinite")));

    renderApp("/gigs/10/edit", { as: asManager });

    expect(await screen.findByRole("status")).toHaveTextContent("Loading the gig…");
  });

  it("shows an error with a retry that works", async () => {
    server.use(
      http.get(
        "*/api/v1/gigs/:gigId",
        () => HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/gigs/10/edit", { as: asManager });

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByLabelText("Venue name")).toHaveValue("The Blue Door");
  });

  it("fills the form with the gig's current details, in local time", async () => {
    renderApp("/gigs/10/edit", { as: asManager });

    expect(await screen.findByLabelText("Venue name")).toHaveValue("The Blue Door");
    expect(screen.getByLabelText("Date")).toHaveValue("2026-10-18");
    expect(screen.getByLabelText("First set time")).toHaveValue("20:00");
    expect(screen.getByLabelText("Soundcheck (minutes before first set)")).toHaveValue("75");
    expect(screen.getByLabelText("Pay (USD, whole gig)")).toHaveValue("400.00");
    expect(screen.getByLabelText("Gig type")).toHaveValue("duo");
    expect(screen.getByLabelText("Venue contact name")).toHaveValue("Pat Lee");
  });

  it("saves changes and returns to the gig", async () => {
    let sent: GigUpdate | undefined;
    server.use(
      http.patch("*/api/v1/gigs/:gigId", async ({ request }) => {
        sent = (await request.json()) as GigUpdate;
        return HttpResponse.json(saveGig({ ...blueDoor, pay_cents: sent.pay_cents ?? null }));
      }),
    );
    const { user, router } = renderApp("/gigs/10/edit", { as: asManager });

    const pay = await screen.findByLabelText("Pay (USD, whole gig)");
    await user.clear(pay);
    await user.type(pay, "450");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("$450.00")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/gigs/10");
    expect(sent?.pay_cents).toBe(45000);
    expect(sent?.first_set_at).toBe("2026-10-19T00:00:00.000Z");
  });

  it("shows the reason when a booked gig would lose something it needs", async () => {
    server.use(
      http.patch("*/api/v1/gigs/:gigId", () =>
        HttpResponse.json(
          errorBody("gig_incomplete", "This gig is booked, so it can't be left without: pay."),
          { status: 409 },
        ),
      ),
    );
    const { user } = renderApp("/gigs/10/edit", { as: asManager });

    await user.clear(await screen.findByLabelText("Pay (USD, whole gig)"));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This gig is booked, so it can't be left without: pay.",
    );
  });

  it("tells a member only the manager can edit gigs", () => {
    renderApp("/gigs/10/edit", { as: asSam });

    expect(screen.getByRole("heading", { level: 1, name: "Manager only" })).toBeInTheDocument();
  });
});
