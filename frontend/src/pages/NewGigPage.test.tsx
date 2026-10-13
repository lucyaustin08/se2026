import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { GigCreate } from "../api/types";
import { asManager, asSam, hubCity } from "../test/fixtures";
import { errorBody, saveGig } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("add gig page", () => {
  it("saves a potential gig with roles and contacts, then opens it", async () => {
    let sent: GigCreate | undefined;
    server.use(
      http.post("*/api/v1/gigs", async ({ request }) => {
        sent = (await request.json()) as GigCreate;
        return HttpResponse.json(
          saveGig({ ...hubCity, id: 99, venue_name: sent.venue_name ?? null }),
          { status: 201 },
        );
      }),
    );
    const { user, router } = renderApp("/gigs/new", { as: asManager });

    await user.type(screen.getByLabelText("Date"), "2026-10-18");
    await user.type(screen.getByLabelText("First set time"), "20:00");
    await user.type(screen.getByLabelText("Venue name"), "The Blue Door");
    await user.type(screen.getByLabelText("Total pay for the gig (USD)"), "400.50");
    await user.click(screen.getByRole("checkbox", { name: "Lead guitar" }));
    await user.click(screen.getByRole("checkbox", { name: "Rhythm guitar / vocals" }));
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    await user.type(screen.getByLabelText("Contact 1 name"), "Pat Lee");
    await user.type(screen.getByLabelText("Contact 1 phone"), "555-0142");
    await user.type(screen.getByLabelText("Contact 1 notes"), "Alley door");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    await user.selectOptions(screen.getByLabelText("Contact 2 type"), "Booking");
    await user.type(screen.getByLabelText("Contact 2 email"), "morgan@example.com");
    await user.click(screen.getByRole("button", { name: "Save gig" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "The Blue Door" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/gigs/99");
    expect(sent).toEqual({
      first_set_at: "2026-10-19T00:00:00.000Z",
      load_in_offset_minutes: 120,
      soundcheck_offset_minutes: 60,
      performance_minutes: 180,
      venue_name: "The Blue Door",
      venue_address: null,
      pay_cents: 40050,
      // Always sent in band order, whatever order they were ticked in.
      roles: ["rhythm_guitar_vocals", "lead_guitar"],
      contacts: [
        { label: "venue", name: "Pat Lee", phone: "555-0142", email: null, notes: "Alley door" },
        { label: "booking", name: null, phone: null, email: "morgan@example.com", notes: null },
      ],
    });
  });

  it("can save a draft with nothing filled in", async () => {
    let sent: GigCreate | undefined;
    server.use(
      http.post("*/api/v1/gigs", async ({ request }) => {
        sent = (await request.json()) as GigCreate;
        return HttpResponse.json(saveGig({ ...hubCity, id: 99, venue_name: null }), {
          status: 201,
        });
      }),
    );
    const { user, router } = renderApp("/gigs/new", { as: asManager });

    await user.click(screen.getByRole("button", { name: "Add contact" }));
    await user.click(screen.getByRole("button", { name: "Save gig" }));

    await screen.findByRole("heading", { level: 1, name: "Untitled gig" });
    expect(router.state.location.pathname).toBe("/gigs/99");
    // A contact row left blank is dropped rather than sent.
    expect(sent?.contacts).toEqual([]);
  });

  it("removes a contact", async () => {
    const { user } = renderApp("/gigs/new", { as: asManager });

    await user.click(screen.getByRole("button", { name: "Add contact" }));
    await user.click(screen.getByRole("button", { name: "Remove contact 1" }));

    expect(screen.queryByLabelText("Contact 1 name")).not.toBeInTheDocument();
    expect(screen.getByText("No contacts yet.")).toBeInTheDocument();
  });

  it.each([
    {
      field: "Date",
      value: "2026-10-18",
      errorOn: "First set time",
      message: "Enter a first set time, or clear the date.",
    },
    {
      field: "First set time",
      value: "20:00",
      errorOn: "Date",
      message: "Enter a date, or clear the first set time.",
    },
    {
      field: "Total pay for the gig (USD)",
      value: "lots",
      errorOn: "Total pay for the gig (USD)",
      message: "Enter pay as a dollar amount, like 400 or 400.50.",
    },
  ])("ties '$message' to $errorOn", async ({ field, value, errorOn, message }) => {
    let posted = false;
    server.use(
      http.post("*/api/v1/gigs", () => {
        posted = true;
        return HttpResponse.json(hubCity, { status: 201 });
      }),
    );
    const { user } = renderApp("/gigs/new", { as: asManager });

    await user.type(screen.getByLabelText(field), value);
    await user.click(screen.getByRole("button", { name: "Save gig" }));

    const input = screen.getByLabelText(errorOn);
    expect(input).toHaveAccessibleDescription(message);
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveFocus();
    expect(posted).toBe(false);
  });

  it("ties an invalid contact email to that contact's email field", async () => {
    const { user } = renderApp("/gigs/new", { as: asManager });

    await user.click(screen.getByRole("button", { name: "Add contact" }));
    const email = screen.getByLabelText("Contact 1 email");
    await user.type(email, "pat-at-example");
    await user.click(screen.getByRole("button", { name: "Save gig" }));

    expect(email).toHaveAccessibleDescription("Enter an email address like name@example.com.");
    expect(email).toHaveFocus();
  });

  it.each([
    ["Load-in (minutes before first set)", "721", "Enter whole minutes from 0 to 720."],
    ["Soundcheck (minutes before first set)", "721", "Enter whole minutes from 0 to 720."],
    ["Length (minutes from first set to the end)", "10", "Enter whole minutes from 15 to 720."],
  ])("checks the range of %s", async (label, value, message) => {
    const { user } = renderApp("/gigs/new", { as: asManager });

    const input = screen.getByLabelText(label);
    await user.clear(input);
    await user.type(input, value);
    await user.click(screen.getByRole("button", { name: "Save gig" }));

    expect(input).toHaveAccessibleDescription(expect.stringContaining(message));
  });

  it("shows the server's message when saving is refused", async () => {
    server.use(
      http.post("*/api/v1/gigs", () =>
        HttpResponse.json(errorBody("validation_error", "The request is invalid."), {
          status: 422,
        }),
      ),
    );
    const { user } = renderApp("/gigs/new", { as: asManager });

    await user.click(screen.getByRole("button", { name: "Save gig" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The request is invalid.");
  });

  it("tells a member only the manager can add gigs", () => {
    renderApp("/gigs/new", { as: asSam });

    expect(screen.getByRole("heading", { level: 1, name: "Manager only" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save gig" })).not.toBeInTheDocument();
  });
});
