import { screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { PracticeCreate } from "../api/types";
import { asCasey, asManager, asRiley, asSam } from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

function practicesRegion() {
  return screen.getByRole("region", { name: "Upcoming practices" });
}

async function openScheduleDialog() {
  const view = renderApp("/scheduling", { as: asSam });
  await view.user.click(await screen.findByRole("button", { name: "Schedule practice" }));
  const dialog = screen.getByRole("dialog", { name: "Schedule practice" });
  await within(dialog).findByRole("group", { name: "Who's invited" });
  return { ...view, dialog };
}

async function fillPractice(
  user: Awaited<ReturnType<typeof openScheduleDialog>>["user"],
  dialog: HTMLElement,
) {
  await user.type(within(dialog).getByLabelText("Date"), "2026-11-19");
  await user.type(within(dialog).getByLabelText("Start time"), "18:00");
  await user.selectOptions(within(dialog).getByLabelText("Length"), "2 hours");
  await user.type(within(dialog).getByLabelText("Location"), "Sam's garage");
  await user.click(within(dialog).getByRole("checkbox", { name: /Riley Chen/ }));
  await user.click(within(dialog).getByRole("checkbox", { name: /Casey Morgan/ }));
}

describe("practices on the scheduling page", () => {
  it("shows a loading message while practices load", async () => {
    server.use(http.get("*/api/v1/practices", () => delay("infinite")));

    renderApp("/scheduling", { as: asRiley });

    expect(await screen.findByText("Loading practices…")).toHaveAttribute("role", "status");
  });

  it("shows an error with a retry that works", async () => {
    let failed = false;
    server.use(
      // Fail only this section's first request (the calendar asks with an end date too).
      http.get("*/api/v1/practices", ({ request }) => {
        if (failed || new URL(request.url).searchParams.has("starts_before")) return undefined;
        failed = true;
        return HttpResponse.json(errorBody("internal_error", "Something broke."), {
          status: 500,
        });
      }),
    );
    const { user } = renderApp("/scheduling", { as: asRiley });

    const region = await screen.findByRole("region", { name: "Upcoming practices" });
    expect(await within(region).findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(within(region).getByRole("button", { name: "Try again" }));

    expect(await within(region).findByText(/Sam's garage/)).toBeInTheDocument();
  });

  it("tells a member when they have no practices", async () => {
    server.use(
      http.get("*/api/v1/practices", () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 100 }),
      ),
    );

    renderApp("/scheduling", { as: asRiley });

    expect(
      await screen.findByText("You haven't been invited to any upcoming practices."),
    ).toBeInTheDocument();
  });

  it("shows an invited member the practice and lets them say they'll be there", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const card = (await within(practicesRegion()).findByText(/Practice ·/)).closest("li");
    expect(card).toHaveTextContent("Practice · Thu, Nov 12, 2026, 6:00 PM – 9:00 PM");
    expect(card).toHaveTextContent("Sam's garage · New songs");
    expect(card).toHaveTextContent("Your answer:Invited");
    // Members see their own answer, not everyone's.
    expect(within(card as HTMLElement).queryByRole("list", { name: "Who's invited" })).toBeNull();

    await user.click(within(card as HTMLElement).getByRole("button", { name: "I'll be there" }));

    expect(await within(practicesRegion()).findByText("Coming")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "I'll be there" })).not.toBeInTheDocument();
  });

  it("lets an invited member decline", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(await screen.findByRole("button", { name: "Can't make it" }));

    await waitFor(() =>
      expect(
        within(practicesRegion())
          .getByText(/Practice ·/)
          .closest("li"),
      ).toHaveTextContent("Your answer:Can't make it"),
    );
    expect(screen.queryByRole("button", { name: "Can't make it" })).not.toBeInTheDocument();
  });

  it("shows a member who already declined their answer without buttons", async () => {
    renderApp("/scheduling", { as: asCasey });

    const card = (await within(practicesRegion()).findByText(/Practice ·/)).closest("li");
    expect(card).toHaveTextContent("Your answer:Can't make it");
    expect(within(card as HTMLElement).queryByRole("button")).toBeNull();
  });

  it("shows the manager who's coming, and no schedule button for members", async () => {
    renderApp("/scheduling", { as: asManager });

    const invited = await within(practicesRegion()).findByRole("list", { name: "Who's invited" });
    expect(invited).toHaveTextContent("Sam Rivera Coming");
    expect(invited).toHaveTextContent("Riley Chen Invited");
    expect(invited).toHaveTextContent("Casey Morgan Can't make it");
    expect(screen.getByRole("button", { name: "Schedule practice" })).toBeInTheDocument();
  });

  it("doesn't offer members a way to schedule", async () => {
    renderApp("/scheduling", { as: asRiley });

    await within(practicesRegion()).findByText(/Practice ·/);
    expect(screen.queryByRole("button", { name: "Schedule practice" })).not.toBeInTheDocument();
  });

  it("schedules a practice for the chosen members", async () => {
    let sent: PracticeCreate | undefined;
    server.use(
      http.post("*/api/v1/practices", async ({ request }) => {
        sent = (await request.json()) as PracticeCreate;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    const { user, dialog } = await openScheduleDialog();

    expect(within(dialog).queryByRole("checkbox", { name: /Jordan Avery/ })).toBeNull();
    await fillPractice(user, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Schedule practice" }));

    expect(sent).toEqual({
      starts_at: "2026-11-19T23:00:00.000Z",
      length_minutes: 120,
      location: "Sam's garage",
      notes: null,
      member_ids: [4, 3],
      confirm_same_day: false,
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ties missing details to their fields", async () => {
    const { user, dialog } = await openScheduleDialog();

    await user.click(within(dialog).getByRole("button", { name: "Schedule practice" }));

    const date = within(dialog).getByLabelText("Date");
    expect(date).toHaveAccessibleDescription("Enter the practice date.");
    expect(date).toHaveFocus();
    expect(within(dialog).getByLabelText("Start time")).toHaveAccessibleDescription(
      "Enter the start time.",
    );
    expect(
      within(dialog).getByRole("group", { name: "Who's invited" }),
    ).toHaveAccessibleDescription("Invite at least one member.");
  });

  it("shows a pop-up error when the practice overlaps a gig, and keeps the form", async () => {
    server.use(
      http.post("*/api/v1/practices", () =>
        HttpResponse.json(
          errorBody(
            "practice_overlaps_gig",
            "This practice overlaps Hub City Tap on Thu, Nov 19 at 8:00 PM. Pick a time that's clear of it.",
          ),
          { status: 409 },
        ),
      ),
    );
    const { user, dialog } = await openScheduleDialog();

    await fillPractice(user, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Schedule practice" }));

    const alert = await within(dialog).findByRole("alert");
    expect(alert).toHaveTextContent("Can't schedule this practice");
    expect(alert).toHaveTextContent("overlaps Hub City Tap on Thu, Nov 19 at 8:00 PM");
    expect(within(dialog).getByLabelText("Date")).toHaveValue("2026-11-19");
  });

  it("warns about a gig the same day and schedules once confirmed", async () => {
    const sent: PracticeCreate[] = [];
    server.use(
      http.post("*/api/v1/practices", async ({ request }) => {
        const body = (await request.json()) as PracticeCreate;
        sent.push(body);
        return body.confirm_same_day
          ? HttpResponse.json({}, { status: 201 })
          : HttpResponse.json(
              errorBody(
                "practice_same_day_as_gig",
                "There's a gig the same day: Hub City Tap on Thu, Nov 19 at 8:00 PM. Schedule the practice anyway?",
              ),
              { status: 409 },
            );
      }),
    );
    const { user, dialog } = await openScheduleDialog();

    await fillPractice(user, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Schedule practice" }));

    const warning = await within(dialog).findByRole("alert");
    expect(warning).toHaveTextContent("Heads up: there's a gig that day");
    await user.click(within(warning).getByRole("button", { name: "Schedule anyway" }));

    expect(sent.map((body) => body.confirm_same_day)).toEqual([false, true]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("lets the scheduler go back and change the time after a same-day warning", async () => {
    server.use(
      http.post("*/api/v1/practices", () =>
        HttpResponse.json(errorBody("practice_same_day_as_gig", "There's a gig the same day."), {
          status: 409,
        }),
      ),
    );
    const { user, dialog } = await openScheduleDialog();

    await fillPractice(user, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Schedule practice" }));
    await user.click(await within(dialog).findByRole("button", { name: "Change the time" }));

    expect(within(dialog).queryByRole("alert")).toBeNull();
    expect(within(dialog).getByLabelText("Date")).toHaveFocus();
    expect(within(dialog).getByRole("button", { name: "Schedule practice" })).toBeInTheDocument();
  });
});
