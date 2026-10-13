import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { InvitationIn } from "../api/types";
import { asManager, asRiley, asSam, blueDoorForSam } from "../test/fixtures";
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

  it("tells a member when they aren't in the lineup", async () => {
    server.use(
      http.get("*/api/v1/gigs/:gigId", () =>
        HttpResponse.json(
          errorBody("not_assigned_to_gig", "You're not in the lineup for this gig."),
          { status: 403 },
        ),
      ),
    );

    renderApp("/gigs/10", { as: asRiley });

    expect(
      await screen.findByRole("heading", { level: 1, name: "Not your gig" }),
    ).toBeInTheDocument();
    expect(screen.getByText("You're not in the lineup for this gig.")).toBeInTheDocument();
  });

  it("shows the day-of times in order, the details and every contact", async () => {
    renderApp("/gigs/10", { as: asManager });

    const schedule = await screen.findByRole("region", { name: "Schedule" });
    expect(within(schedule).getByText("Sun, Oct 18, 2026")).toBeInTheDocument();
    expect(
      within(schedule)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Load-in6:00 PM", "Soundcheck6:45 PM", "First set8:00 PM", "End11:00 PM"]);

    const details = screen.getByRole("region", { name: "Details" });
    expect(details).toHaveTextContent("123 Main St, Spartanburg, SC");
    expect(details).toHaveTextContent("Duo");
    expect(details).toHaveTextContent("Total pay$400.00");

    const contacts = screen.getByRole("region", { name: "Contacts" });
    expect(contacts).toHaveTextContent("Venue: Pat Lee · 555-0142");
    expect(contacts).toHaveTextContent("Load in through the alley door.");
  });

  it("shows a member their gig read-only, with only their own pay", async () => {
    server.use(http.get("*/api/v1/gigs/:gigId", () => HttpResponse.json(blueDoorForSam)));

    renderApp("/gigs/10", { as: asSam });

    const invitation = await screen.findByRole("region", { name: "Your invitation" });
    expect(invitation).toHaveTextContent("Role: Rhythm guitar / vocals");
    expect(invitation).toHaveTextContent("Your pay: $200.00");
    expect(invitation).toHaveTextContent("Accepted");
    expect(within(invitation).queryByRole("button")).not.toBeInTheDocument();

    const lineup = screen.getByRole("region", { name: "Lineup" });
    expect(lineup).toHaveTextContent("Lead guitar: Casey Morgan");
    expect(screen.getByRole("region", { name: "Details" })).not.toHaveTextContent("pay");
    expect(screen.queryByRole("link", { name: "Edit details" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Book gig" })).not.toBeInTheDocument();
  });

  it("lets an invited member accept", async () => {
    const { user } = renderApp("/gigs/14", { as: asRiley });

    const invitation = await screen.findByRole("region", { name: "Your invitation" });
    expect(invitation).toHaveTextContent("Role: Bass");
    expect(invitation).toHaveTextContent("Your pay: $150.00");

    await user.click(within(invitation).getByRole("button", { name: "Accept" }));

    expect(await within(invitation).findByText("Accepted")).toBeInTheDocument();
    expect(within(invitation).queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
  });

  it("lets an invited member decline", async () => {
    const { user } = renderApp("/gigs/14", { as: asRiley });

    const invitation = await screen.findByRole("region", { name: "Your invitation" });
    await user.click(within(invitation).getByRole("button", { name: "Decline" }));

    expect(await within(invitation).findByText("Declined")).toBeInTheDocument();
  });

  it("explains when accepting would double-book the member", async () => {
    server.use(
      http.post("*/api/v1/gigs/:gigId/slots/:slotId/accept", () =>
        HttpResponse.json(
          errorBody(
            "overlapping_gig",
            "You've already accepted another gig at the same time (The Blue Door).",
          ),
          { status: 409 },
        ),
      ),
    );
    const { user } = renderApp("/gigs/14", { as: asRiley });

    const invitation = await screen.findByRole("region", { name: "Your invitation" });
    await user.click(within(invitation).getByRole("button", { name: "Accept" }));

    expect(await within(invitation).findByRole("alert")).toHaveTextContent(
      "You've already accepted another gig at the same time (The Blue Door).",
    );
    expect(invitation).toHaveTextContent("Invited, waiting for an answer");
  });

  it("shows the manager every slot with who was asked and their answer", async () => {
    renderApp("/gigs/11", { as: asManager });

    const lineup = await screen.findByRole("region", { name: "Lineup" });
    const slots = await within(lineup).findAllByRole("heading", { level: 3 });
    expect(slots.map((heading) => heading.textContent)).toEqual([
      "Rhythm guitar / vocals",
      "Lead guitar",
      "Bass",
      "Drums",
    ]);
    expect(lineup).toHaveTextContent("Sam Rivera · Invited, waiting for an answer");
    expect(lineup).toHaveTextContent("Casey Morgan · Accepted · $150.00");
    expect(lineup).toHaveTextContent("Riley Chen · Declined");
    expect(lineup).toHaveTextContent("Nobody invited yet");
    // Accepted slots can't be re-invited; every other slot can.
    expect(within(lineup).queryByLabelText("Invite for Lead guitar")).not.toBeInTheDocument();
    expect(within(lineup).getByLabelText("Invite for Drums")).toBeInTheDocument();
  });

  it("lists usual players first and everyone else as backups", async () => {
    renderApp("/gigs/11", { as: asManager });

    const select = await screen.findByLabelText("Invite for Bass");
    const groups = within(select).getAllByRole("group");
    expect(groups.map((group) => group.getAttribute("label"))).toEqual(["Plays Bass", "Backups"]);
    expect(
      within(groups[0])
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Riley Chen"]);
    expect(
      within(groups[1])
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Sam Rivera", "Casey Morgan"]);
  });

  it("sends an invitation with the member's pay", async () => {
    let sent: InvitationIn | undefined;
    server.use(
      http.post("*/api/v1/gigs/:gigId/slots/:slotId/invite", async ({ request }) => {
        sent = (await request.json()) as InvitationIn;
        return HttpResponse.json(
          errorBody("member_in_two_slots", "Casey Morgan is already on this gig."),
          { status: 409 },
        );
      }),
    );
    const { user } = renderApp("/gigs/11", { as: asManager });

    await user.selectOptions(await screen.findByLabelText("Invite for Drums"), "Casey Morgan");
    await user.type(screen.getByLabelText("Pay for Drums (USD)"), "125.50");
    await user.click(screen.getAllByRole("button", { name: "Send invitation" })[0]);

    expect(sent).toEqual({ member_id: 3, pay_cents: 12550 });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Casey Morgan is already on this gig.",
    );
  });

  it("shows the invitation once it's sent", async () => {
    const { user } = renderApp("/gigs/11", { as: asManager });

    const select = await screen.findByLabelText("Invite for Bass");
    const form = select.closest("form") as HTMLElement;
    await user.selectOptions(select, "Riley Chen");
    await user.click(within(form).getByRole("button", { name: "Send new invitation" }));

    expect(
      await screen.findByText("Riley Chen · Invited, waiting for an answer"),
    ).toBeInTheDocument();
  });

  it("ties an invalid pay amount to the pay field", async () => {
    const { user } = renderApp("/gigs/11", { as: asManager });

    await user.selectOptions(await screen.findByLabelText("Invite for Drums"), "Sam Rivera");
    const pay = screen.getByLabelText("Pay for Drums (USD)");
    await user.type(pay, "lots");
    await user.click(screen.getAllByRole("button", { name: "Send invitation" })[0]);

    expect(pay).toHaveAccessibleDescription("Enter pay as a dollar amount, like 150 or 150.50.");
  });

  it("shows an error with a retry if band members can't load", async () => {
    server.use(
      http.get(
        "*/api/v1/members",
        () => HttpResponse.json(errorBody("internal_error", "Members broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/gigs/11", { as: asManager });

    expect(await screen.findByRole("alert")).toHaveTextContent("Members broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByLabelText("Invite for Drums")).toBeInTheDocument();
  });

  it("lists what's still needed and shows the refusal when booking too early", async () => {
    const { user } = renderApp("/gigs/11", { as: asManager });

    const booking = await screen.findByRole("region", { name: "Booking" });
    expect(
      within(booking)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toContain("the band leader, accepted into the lineup");

    await user.click(within(booking).getByRole("button", { name: "Book gig" }));

    expect(await within(booking).findByRole("alert")).toHaveTextContent(
      "This gig can't be booked until it has: venue address, pay",
    );
    expect(screen.getByText("Potential")).toBeInTheDocument();
  });

  it("books a gig once everyone has accepted", async () => {
    const { user } = renderApp("/gigs/12", { as: asManager });

    const booking = await screen.findByRole("region", { name: "Booking" });
    expect(booking).toHaveTextContent("Everyone has accepted");

    await user.click(within(booking).getByRole("button", { name: "Book gig" }));

    expect(await screen.findByText("Booked")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Booking" })).not.toBeInTheDocument();
  });
});
