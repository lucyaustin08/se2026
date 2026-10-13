import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { asManager, asRiley, asSam } from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("gig detail page", () => {
  it("shows a loading message while the gig loads", async () => {
    server.use(http.get("*/api/v1/gigs/:gigId", () => delay("infinite")));

    renderApp("/gigs/10", { as: asManager });

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
    const { user } = renderApp("/gigs/10", { as: asManager });

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "The Blue Door" }),
    ).toBeInTheDocument();
  });

  it("says when the gig doesn't exist", async () => {
    renderApp("/gigs/404", { as: asManager });

    expect(
      await screen.findByRole("heading", { level: 1, name: "Gig not found" }),
    ).toBeInTheDocument();
    expect(screen.getByText("That gig doesn't exist.")).toBeInTheDocument();
  });

  it("tells a member when they aren't on the gig", async () => {
    server.use(
      http.get("*/api/v1/gigs/:gigId", () =>
        HttpResponse.json(errorBody("not_assigned_to_gig", "You're not assigned to this gig."), {
          status: 403,
        }),
      ),
    );

    renderApp("/gigs/10", { as: asRiley });

    expect(
      await screen.findByRole("heading", { level: 1, name: "Not your gig" }),
    ).toBeInTheDocument();
    expect(screen.getByText("You're not assigned to this gig.")).toBeInTheDocument();
  });

  it("shows the day-of times in order, with the venue, pay and contact", async () => {
    renderApp("/gigs/10", { as: asManager });

    const schedule = await screen.findByRole("region", { name: "Schedule" });
    expect(within(schedule).getByText("Sun, Oct 18, 2026")).toBeInTheDocument();
    expect(
      within(schedule)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Load-in6:00 PM", "Soundcheck6:45 PM", "First set8:00 PM"]);

    const details = screen.getByRole("region", { name: "Details" });
    expect(details).toHaveTextContent("123 Main St, Spartanburg, SC");
    expect(details).toHaveTextContent("$400.00");
    expect(details).toHaveTextContent("Pat Lee · 555-0142");
    expect(screen.getByText("Booked")).toBeInTheDocument();
  });

  it("shows a member their gig read-only, without pay", async () => {
    renderApp("/gigs/10", { as: asSam });

    const lineup = await screen.findByRole("region", { name: "Lineup" });
    expect(lineup).toHaveTextContent("Rhythm guitar / vocals: Sam Rivera");
    expect(lineup).toHaveTextContent("Lead guitar: Casey Morgan");
    expect(within(lineup).queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Details" })).not.toHaveTextContent("Pay");
    expect(screen.queryByRole("link", { name: "Edit details" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Book gig" })).not.toBeInTheDocument();
  });

  it("lists what's still needed and shows the refusal when booking an incomplete gig", async () => {
    const { user } = renderApp("/gigs/11", { as: asManager });

    const booking = await screen.findByRole("region", { name: "Booking" });
    expect(
      within(booking)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["venue address", "pay", "a contact with a name and a phone number or email"]);

    await user.click(within(booking).getByRole("button", { name: "Book gig" }));

    expect(await within(booking).findByRole("alert")).toHaveTextContent(
      "This gig can't be booked until it has: venue address, pay",
    );
    expect(screen.getByText("Potential")).toBeInTheDocument();
  });

  it("books a complete gig", async () => {
    const { user } = renderApp("/gigs/12", { as: asManager });

    const booking = await screen.findByRole("region", { name: "Booking" });
    expect(booking).toHaveTextContent("Everything booking needs is filled in.");

    await user.click(within(booking).getByRole("button", { name: "Book gig" }));

    expect(await screen.findByText("Booked")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Booking" })).not.toBeInTheDocument();
  });

  it("lets the manager fill lineup slots with members who play that role", async () => {
    const { user } = renderApp("/gigs/12", { as: asManager });

    const lead = await screen.findByRole("combobox", { name: "Lead guitar" });
    expect(
      within(lead)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Open", "Casey Morgan"]);

    await user.selectOptions(lead, "Casey Morgan");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));

    expect(await screen.findByText("Lineup saved.")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Lead guitar" })).toHaveValue("3");
  });

  it("shows the server's reason when a lineup is refused", async () => {
    server.use(
      http.patch("*/api/v1/gigs/:gigId", () =>
        HttpResponse.json(
          errorBody("member_role_mismatch", "Casey Morgan can't fill the bass slot."),
          { status: 409 },
        ),
      ),
    );
    const { user } = renderApp("/gigs/12", { as: asManager });

    await user.selectOptions(await screen.findByRole("combobox", { name: "Lead guitar" }), "3");
    await user.click(screen.getByRole("button", { name: "Save lineup" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Casey Morgan can't fill the bass slot.",
    );
  });

  it("shows an error with a retry if band members can't load for the lineup", async () => {
    server.use(
      http.get(
        "*/api/v1/members",
        () => HttpResponse.json(errorBody("internal_error", "Members broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/gigs/12", { as: asManager });

    expect(await screen.findByRole("alert")).toHaveTextContent("Members broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("combobox", { name: "Lead guitar" })).toBeInTheDocument();
  });
});
