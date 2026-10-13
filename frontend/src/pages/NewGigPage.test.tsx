import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { GigCreate } from "../api/types";
import { asManager, asSam, hubCity } from "../test/fixtures";
import { errorBody, saveGig } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("add gig page", () => {
  it("saves a potential gig and opens it", async () => {
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
    await user.selectOptions(screen.getByLabelText("Gig type"), "Duo");
    await user.type(screen.getByLabelText("Pay (USD, whole gig)"), "400.50");
    await user.type(screen.getByLabelText("Venue contact name"), "Pat Lee");
    await user.type(screen.getByLabelText("Venue contact phone"), "555-0142");
    await user.click(screen.getByRole("button", { name: "Save gig" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "The Blue Door" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/gigs/99");
    expect(sent).toEqual({
      first_set_at: "2026-10-19T00:00:00.000Z",
      load_in_offset_minutes: 120,
      soundcheck_offset_minutes: 60,
      venue_name: "The Blue Door",
      venue_address: null,
      gig_type: "duo",
      pay_cents: 40050,
      venue_contact: { name: "Pat Lee", phone: "555-0142", email: null },
      booking_contact: null,
    });
  });

  it("can save a draft with nothing filled in", async () => {
    const { user, router } = renderApp("/gigs/new", { as: asManager });

    await user.click(screen.getByRole("button", { name: "Save gig" }));

    await screen.findByRole("heading", { level: 1, name: "Untitled gig" });
    expect(router.state.location.pathname).toBe("/gigs/99");
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
      field: "Pay (USD, whole gig)",
      value: "lots",
      errorOn: "Pay (USD, whole gig)",
      message: "Enter pay as a dollar amount, like 400 or 400.50.",
    },
    {
      field: "Venue contact email",
      value: "pat-at-example",
      errorOn: "Venue contact email",
      message: "Enter an email address like name@example.com.",
    },
    {
      field: "Booking contact email",
      value: "nope",
      errorOn: "Booking contact email",
      message: "Enter an email address like name@example.com.",
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

  it.each(["Load-in (minutes before first set)", "Soundcheck (minutes before first set)"])(
    "requires whole minutes from 0 to 720 for %s",
    async (label) => {
      const { user } = renderApp("/gigs/new", { as: asManager });

      const input = screen.getByLabelText(label);
      await user.clear(input);
      await user.type(input, "721");
      await user.click(screen.getByRole("button", { name: "Save gig" }));

      expect(input).toHaveAccessibleDescription(
        expect.stringContaining("Enter whole minutes from 0 to 720."),
      );
    },
  );

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
