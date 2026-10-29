import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { asManager, asRiley } from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

// The fixtures in November 2026: Hub City Tap (pending gig) on Mon, Nov 2 at 8:00 PM; Riley
// busy Tue, Nov 10, 6–9 PM; a practice Thu, Nov 12, 6–9 PM; Casey away Fri, Nov 13 to Sun, Nov 15;
// Sam busy every Wednesday, 6–9 PM, starting Nov 18.

function calendar() {
  return screen.getByRole("region", { name: /November 2026|Nov \d+ – / });
}

function dayButton(name: RegExp) {
  return within(calendar()).getByRole("button", { name });
}

function dayDetails() {
  return within(calendar()).getByRole("region", { name: /day, / });
}

describe("band calendar", () => {
  it("says it's loading while the calendar's data loads", async () => {
    server.use(http.get("*/api/v1/gigs", () => delay("infinite")));

    renderApp("/scheduling?date=2026-11-12", { as: asManager });

    expect(await screen.findByText("Loading the calendar…")).toHaveAttribute("role", "status");
  });

  it("shows the month with gigs, practices and busy times on their days", async () => {
    renderApp("/scheduling?date=2026-11-12", { as: asManager });

    expect(
      await screen.findByRole("heading", { level: 2, name: "November 2026" }),
    ).toBeInTheDocument();
    expect(
      await within(calendar()).findByRole("button", {
        name: "Monday, November 2, 2026, 1 item",
      }),
    ).toBeInTheDocument();
    expect(
      await within(calendar()).findByRole("button", {
        name: "Tuesday, November 10, 2026, 1 item",
      }),
    ).toBeInTheDocument();
    for (const day of ["Friday, November 13", "Saturday, November 14", "Sunday, November 15"]) {
      expect(dayButton(new RegExp(`^${day}, 2026, 1 item$`))).toBeInTheDocument();
    }
    expect(dayButton(/^Wednesday, November 11, 2026$/)).toBeInTheDocument();
    // Weeks run Sunday to Saturday, so the grid starts on Nov 1 and ends on Dec 5.
    expect(dayButton(/^Saturday, December 5, 2026$/)).toBeInTheDocument();
  });

  it("lists the chosen day's details underneath, with each kind named in words", async () => {
    renderApp("/scheduling?date=2026-11-12", { as: asManager });

    const details = await within(calendar()).findByRole("region", {
      name: "Thursday, November 12, 2026",
    });
    expect(
      await within(details).findByText("Practice at Sam's garage, 6:00 PM – 9:00 PM"),
    ).toBeInTheDocument();
    expect(within(details).getByText("Practice", { selector: "span" })).toBeInTheDocument();
  });

  it("puts a weekly busy time on each of its days, and says it repeats", async () => {
    renderApp("/scheduling?date=2026-11-18", { as: asManager });

    expect(
      await within(calendar()).findByRole("button", {
        name: "Wednesday, November 18, 2026, 1 item",
      }),
    ).toBeInTheDocument();
    expect(dayButton(/^Wednesday, November 25, 2026, 1 item$/)).toBeInTheDocument();
    expect(dayButton(/^Wednesday, December 2, 2026, 1 item$/)).toBeInTheDocument();
    // It starts on Nov 18, so the Wednesday before is clear.
    expect(dayButton(/^Wednesday, November 11, 2026$/)).toBeInTheDocument();
    expect(
      within(dayDetails()).getByText("Sam Rivera is busy, 6:00 PM – 9:00 PM, every week"),
    ).toBeInTheDocument();
  });

  it("selects a day when it's clicked", async () => {
    const { user, router } = renderApp("/scheduling?date=2026-11-12", { as: asManager });

    await user.click(
      await within(calendar()).findByRole("button", { name: /^Tuesday, November 10, 2026/ }),
    );

    expect(dayButton(/^Tuesday, November 10, 2026/)).toHaveAttribute("aria-pressed", "true");
    expect(dayDetails()).toHaveAccessibleName("Tuesday, November 10, 2026");
    expect(
      await within(dayDetails()).findByText("Riley Chen is busy, 6:00 PM – 9:00 PM"),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe("?date=2026-11-10&view=month");
  });

  it("moves between days with the arrow keys", async () => {
    const { user } = renderApp("/scheduling?date=2026-11-12", { as: asManager });

    const selected = await within(calendar()).findByRole("button", {
      name: /^Thursday, November 12, 2026/,
    });
    // Only the chosen day is in the tab order; arrows move from there.
    expect(selected).toHaveAttribute("tabindex", "0");
    selected.focus();
    await user.keyboard("{ArrowRight}");

    expect(dayButton(/^Friday, November 13, 2026/)).toHaveFocus();
    await user.keyboard("{ArrowUp}");
    expect(dayButton(/^Friday, November 6, 2026/)).toHaveFocus();
  });

  it("steps to the next and previous month, and back to today", async () => {
    const { user } = renderApp("/scheduling?date=2026-11-12", { as: asManager });

    await user.click(await screen.findByRole("button", { name: "Next month" }));
    expect(screen.getByRole("heading", { level: 2, name: "December 2026" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Previous month" }));
    await user.click(screen.getByRole("button", { name: "Previous month" }));
    expect(screen.getByRole("heading", { level: 2, name: "October 2026" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Today" }));
    expect(screen.getByRole("button", { name: new RegExp(`^${todayName()}`) })).toHaveAttribute(
      "aria-current",
      "date",
    );
  });

  it("switches to a week view", async () => {
    const { user } = renderApp("/scheduling?date=2026-11-12", { as: asManager });

    await user.click(await screen.findByRole("button", { name: "Week" }));

    expect(screen.getByRole("button", { name: "Week" })).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("heading", { level: 2, name: "Nov 8 – Nov 14, 2026" }),
    ).toBeInTheDocument();
    expect(dayButton(/^Sunday, November 8, 2026$/)).toBeInTheDocument();
    expect(dayButton(/^Saturday, November 14, 2026, 1 item$/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next week" }));
    expect(
      screen.getByRole("heading", { level: 2, name: "Nov 15 – Nov 21, 2026" }),
    ).toBeInTheDocument();
  });

  it("shows a key with each player's initials and name for the manager", async () => {
    renderApp("/scheduling?date=2026-11-12", { as: asManager });

    const key = await within(calendar()).findByRole("region", { name: "Key" });
    expect(await within(key).findByText("Riley Chen Busy", { exact: false })).toBeInTheDocument();
    expect(key).toHaveTextContent("RC Riley Chen Busy");
    expect(key).toHaveTextContent("CM Casey Morgan Busy");
    expect(key).not.toHaveTextContent("Jordan Avery");
  });

  it("shows a member only their own color in the key", async () => {
    renderApp("/scheduling?date=2026-11-12", { as: asRiley });

    const key = await within(calendar()).findByRole("region", { name: "Key" });
    expect(await within(key).findByText(/Riley Chen Busy/)).toBeInTheDocument();
    expect(key).not.toHaveTextContent("Casey Morgan");
  });

  it("shows an error with a retry that works", async () => {
    server.use(
      http.get(
        "*/api/v1/gigs",
        () => HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/scheduling?date=2026-11-12", { as: asManager });

    expect(await within(calendar()).findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(within(calendar()).getByRole("button", { name: "Try again" }));

    expect(
      await within(calendar()).findByRole("button", { name: "Monday, November 2, 2026, 1 item" }),
    ).toBeInTheDocument();
  });

  it("opens on today when the address has no date", async () => {
    renderApp("/scheduling", { as: asManager });

    expect(
      await screen.findByRole("button", { name: new RegExp(`^${todayName()}`) }),
    ).toHaveAttribute("aria-current", "date");
  });
});

function todayName(): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date());
}
