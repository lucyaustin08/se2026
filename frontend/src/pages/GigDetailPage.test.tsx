import { screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { InvitationIn } from "../api/types";
import {
  asCasey,
  asManager,
  asRiley,
  asSam,
  blueDoorForCasey,
  blueDoorForSam,
  hubCity,
  riley,
} from "../test/fixtures";
import { availabilityFor, errorBody } from "../test/handlers";
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

  it("shows a member their gig read-only, with only their own pay and no contacts", async () => {
    server.use(http.get("*/api/v1/gigs/:gigId", () => HttpResponse.json(blueDoorForCasey)));

    renderApp("/gigs/10", { as: asCasey });

    const invitation = await screen.findByRole("region", { name: "Your invitation" });
    expect(invitation).toHaveTextContent("Role: Lead guitar");
    expect(invitation).toHaveTextContent("Your pay: $200.00");
    expect(invitation).toHaveTextContent("Accepted");
    expect(within(invitation).queryByRole("button")).not.toBeInTheDocument();

    const lineup = screen.getByRole("region", { name: "Lineup" });
    expect(lineup).toHaveTextContent("Rhythm guitar / vocals: Sam Rivera");
    expect(lineup).not.toHaveTextContent("$");
    expect(screen.getByRole("region", { name: "Details" })).not.toHaveTextContent("pay");
    expect(screen.queryByRole("region", { name: "Contacts" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Edit details" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Book gig" })).not.toBeInTheDocument();
  });

  it("shows the band leader everything, with the manager's lineup and edit tools", async () => {
    server.use(http.get("*/api/v1/gigs/:gigId", () => HttpResponse.json(blueDoorForSam)));

    renderApp("/gigs/10", { as: asSam });

    const invitation = await screen.findByRole("region", { name: "Your invitation" });
    expect(invitation).toHaveTextContent("Your pay: $200.00");

    expect(screen.getByRole("region", { name: "Details" })).toHaveTextContent("Total pay$400.00");
    const lineup = screen.getByRole("region", { name: "Lineup" });
    await waitFor(() => expect(lineup).toHaveTextContent("Casey Morgan · Accepted · $200.00"));
    expect(screen.getByRole("region", { name: "Contacts" })).toHaveTextContent(
      "Venue: Pat Lee · 555-0142",
    );
    expect(screen.getByRole("link", { name: "Edit details" })).toBeInTheDocument();
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

  it("lists usual players first, then secondary players, then everyone else as backups", async () => {
    renderApp("/gigs/11", { as: asManager });

    const select = await screen.findByLabelText("Invite for Bass");
    // Secondary instruments come with the gig's availability, which loads after the lineup.
    await waitFor(() =>
      expect(
        within(select)
          .getAllByRole("group")
          .map((g) => g.getAttribute("label")),
      ).toEqual(["Plays Bass", "Also plays Bass", "Backups"]),
    );
    const options = (group: number) =>
      within(within(select).getAllByRole("group")[group])
        .getAllByRole("option")
        .map((o) => o.textContent);
    expect(options(0)).toEqual(["Riley Chen"]);
    expect(options(1)).toEqual(["Sam Rivera"]);
    expect(options(2)).toEqual(["Casey Morgan"]);
  });

  it("marks busy players and says why, but still lets them be invited", async () => {
    server.use(
      http.get("*/api/v1/gigs/:gigId/availability", () => {
        const availability = availabilityFor(hubCity);
        return HttpResponse.json({
          ...availability,
          players: availability.players.map((player) =>
            player.member.id === riley.id
              ? {
                  ...player,
                  busy: true,
                  conflicts: [
                    {
                      kind: "busy_time",
                      starts_at: "2026-10-23T22:00:00Z",
                      ends_at: "2026-10-24T01:00:00Z",
                      gig_id: null,
                      venue_name: null,
                    },
                    {
                      kind: "gig",
                      starts_at: "2026-10-23T23:00:00Z",
                      ends_at: "2026-10-24T03:00:00Z",
                      gig_id: 10,
                      venue_name: "The Blue Door",
                    },
                  ],
                }
              : player,
          ),
        });
      }),
    );
    const { user } = renderApp("/gigs/11", { as: asManager });

    const select = await screen.findByLabelText("Invite for Bass");
    const busyOption = await within(select).findByRole("option", { name: "Riley Chen · Busy" });
    await user.selectOptions(select, busyOption);

    expect(select).toHaveAccessibleDescription(
      "Riley Chen is busy then: marked busy Fri, Oct 23, 2026, 6:00 PM – 9:00 PM; playing The Blue Door. You can still invite them.",
    );
    expect(
      within(select.closest("form") as HTMLElement).getByRole("button", { name: /invitation/ }),
    ).toBeEnabled();
  });

  it("says when a player is busy because of a weekly busy time", async () => {
    server.use(
      http.get("*/api/v1/gigs/:gigId/availability", () => {
        const availability = availabilityFor(hubCity);
        return HttpResponse.json({
          ...availability,
          players: availability.players.map((player) =>
            player.member.id === riley.id
              ? {
                  ...player,
                  busy: true,
                  conflicts: [
                    {
                      kind: "weekly_busy_time",
                      starts_at: "2026-11-02T23:00:00Z",
                      ends_at: "2026-11-03T02:00:00Z",
                      gig_id: null,
                      venue_name: null,
                    },
                  ],
                }
              : player,
          ),
        });
      }),
    );
    const { user } = renderApp("/gigs/11", { as: asManager });

    const select = await screen.findByLabelText("Invite for Bass");
    await user.selectOptions(
      select,
      await within(select).findByRole("option", { name: "Riley Chen · Busy" }),
    );

    expect(select).toHaveAccessibleDescription(
      "Riley Chen is busy then: busy every week Mon, Nov 2, 2026, 6:00 PM – 9:00 PM. You can still invite them.",
    );
  });

  it("says busy marks need a date when the gig has none", async () => {
    server.use(
      http.get("*/api/v1/gigs/:gigId/availability", () =>
        HttpResponse.json({
          ...availabilityFor(hubCity),
          window_starts_at: null,
          window_ends_at: null,
        }),
      ),
    );
    renderApp("/gigs/11", { as: asManager });

    const select = await screen.findByLabelText("Invite for Bass");

    await waitFor(() =>
      expect(select).toHaveAccessibleDescription("Add a date and time to see who's busy."),
    );
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
    expect(screen.getByText("Pending")).toBeInTheDocument();
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
