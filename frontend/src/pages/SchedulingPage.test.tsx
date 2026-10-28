import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { BusyTimeIn, RecurringBusyTimeIn } from "../api/types";
import { asCasey, asManager, asRiley, asSam } from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

const emptyPage = { items: [], total: 0, page: 1, page_size: 100 };

function mine() {
  return screen.getByRole("region", { name: "Your busy times" });
}

describe("scheduling page: your busy times", () => {
  it("shows a loading message while busy times load", async () => {
    server.use(http.get("*/api/v1/busy-times", () => delay("infinite")));

    renderApp("/scheduling", { as: asRiley });

    expect(await screen.findByText("Loading your busy times…")).toHaveAttribute("role", "status");
  });

  it("shows an error with a retry that works", async () => {
    server.use(
      http.get(
        "*/api/v1/busy-times",
        () => HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/scheduling", { as: asRiley });

    const region = await screen.findByRole("region", { name: "Your busy times" });
    expect(await within(region).findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(within(region).getByRole("button", { name: "Try again" }));

    expect(await within(mine()).findByText(/Tue, Nov 10, 2026/)).toBeInTheDocument();
  });

  it("says a member with no busy times counts as available", async () => {
    server.use(http.get("*/api/v1/busy-times", () => HttpResponse.json(emptyPage)));

    renderApp("/scheduling", { as: asRiley });

    expect(
      await screen.findByText("You haven't marked any busy times, so you count as available."),
    ).toBeInTheDocument();
  });

  it("lists a member's own busy times with a word, not just a color", async () => {
    renderApp("/scheduling", { as: asRiley });

    const row = (await within(mine()).findByText(/Tue, Nov 10, 2026/)).closest("li");
    expect(row).toHaveTextContent("BusyTue, Nov 10, 2026, 6:00 PM – 9:00 PM");
    // Only their own: Casey's trip isn't listed.
    expect(within(mine()).queryByText(/Nov 13/)).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Everyone's busy times" })).not.toBeInTheDocument();
  });

  it("adds a one-off busy time from the pop-up", async () => {
    let sent: BusyTimeIn | undefined;
    server.use(
      http.post("*/api/v1/busy-times", async ({ request }) => {
        sent = (await request.json()) as BusyTimeIn;
        return HttpResponse.json(
          {
            id: 950,
            member: { id: 4, name: "Riley Chen" },
            ...sent,
            created_at: "2026-10-28T12:00:00Z",
          },
          { status: 201 },
        );
      }),
    );
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(await screen.findByRole("button", { name: "Add busy time" }));
    const dialog = screen.getByRole("dialog", { name: "Add busy time" });
    // It starts on the choice of how often, set to one-off.
    const oneOff = within(dialog).getByRole("radio", { name: "One-off" });
    expect(oneOff).toHaveFocus();
    expect(oneOff).toBeChecked();
    await user.type(within(dialog).getByLabelText("Start date"), "2026-11-20");
    await user.type(within(dialog).getByLabelText("Start time"), "18:00");
    // The end date follows the start date until it's changed.
    expect(within(dialog).getByLabelText("End date")).toHaveValue("2026-11-20");
    await user.type(within(dialog).getByLabelText("End time"), "21:30");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(sent).toEqual({
      starts_at: "2026-11-20T23:00:00.000Z",
      ends_at: "2026-11-21T02:30:00.000Z",
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("ties a missing time to its field", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(await screen.findByRole("button", { name: "Add busy time" }));
    const dialog = screen.getByRole("dialog", { name: "Add busy time" });
    await user.type(within(dialog).getByLabelText("Start date"), "2026-11-20");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    const startTime = within(dialog).getByLabelText("Start time");
    expect(startTime).toHaveAccessibleDescription("Enter the time it starts.");
    expect(startTime).toHaveFocus();
  });

  it("won't save a busy time that ends before it starts", async () => {
    let posted = false;
    server.use(
      http.post("*/api/v1/busy-times", () => {
        posted = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(await screen.findByRole("button", { name: "Add busy time" }));
    const dialog = screen.getByRole("dialog", { name: "Add busy time" });
    await user.type(within(dialog).getByLabelText("Start date"), "2026-11-20");
    await user.type(within(dialog).getByLabelText("Start time"), "21:00");
    await user.type(within(dialog).getByLabelText("End time"), "18:00");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(within(dialog).getByLabelText("End time")).toHaveAccessibleDescription(
      "The end has to be after the start.",
    );
    expect(posted).toBe(false);
  });

  it("closes the pop-up with Escape and puts focus back", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const opener = await screen.findByRole("button", { name: "Add busy time" });
    await user.click(opener);
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("changes a busy time, starting from its current times", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(
      await screen.findByRole("button", {
        name: "Change busy time Tue, Nov 10, 2026, 6:00 PM – 9:00 PM",
      }),
    );
    const dialog = screen.getByRole("dialog", { name: "Change busy time" });
    expect(within(dialog).getByLabelText("Start time")).toHaveValue("18:00");
    const end = within(dialog).getByLabelText("End time");
    await user.clear(end);
    await user.type(end, "22:00");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    expect(await within(mine()).findByText(/6:00 PM – 10:00 PM/)).toBeInTheDocument();
  });

  it("deletes a busy time", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(
      await screen.findByRole("button", {
        name: "Delete busy time Tue, Nov 10, 2026, 6:00 PM – 9:00 PM",
      }),
    );

    expect(
      await screen.findByText("You haven't marked any busy times, so you count as available."),
    ).toBeInTheDocument();
  });

  it("shows a refused change in the pop-up", async () => {
    server.use(
      http.patch("*/api/v1/busy-times/:busyTimeId", () =>
        HttpResponse.json(
          errorBody("not_your_busy_time", "You can only change your own busy times."),
          { status: 403 },
        ),
      ),
    );
    const { user } = renderApp("/scheduling", { as: asRiley });

    await user.click(await screen.findByRole("button", { name: /Change busy time/ }));
    const dialog = screen.getByRole("dialog", { name: "Change busy time" });
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "You can only change your own busy times.",
    );
  });
});

describe("scheduling page: everyone's busy times", () => {
  it("shows the manager everyone's busy times by member, and none of their own", async () => {
    renderApp("/scheduling", { as: asManager });

    const band = await screen.findByRole("region", { name: "Everyone's busy times" });
    expect(await within(band).findByRole("heading", { name: "Casey Morgan" })).toBeInTheDocument();
    expect(within(band).getByRole("heading", { name: "Riley Chen" })).toBeInTheDocument();
    expect(band).toHaveTextContent("Fri, Nov 13, 2026, 9:00 AM – Sun, Nov 15, 2026, 6:00 PM");
    // Weekly busy times are listed with the member too.
    const sam = within(band).getByRole("heading", { name: "Sam Rivera" }).closest("li");
    expect(sam).toHaveTextContent(
      "Every week: Wed, 6:00 PM – 9:00 PM · Starting Wed, Nov 18, 2026",
    );
    expect(screen.queryByRole("region", { name: "Your busy times" })).not.toBeInTheDocument();
  });

  it("shows the band leader their own busy times and everyone's", async () => {
    renderApp("/scheduling", { as: asSam });

    expect(await screen.findByRole("region", { name: "Your busy times" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Everyone's busy times" })).toBeInTheDocument();
  });

  it("says when nobody has marked busy times", async () => {
    server.use(
      http.get("*/api/v1/busy-times", () => HttpResponse.json(emptyPage)),
      http.get("*/api/v1/recurring-busy-times", () => HttpResponse.json(emptyPage)),
    );

    renderApp("/scheduling", { as: asManager });

    expect(
      await screen.findByText("Nobody has marked any busy times. Everyone is available."),
    ).toBeInTheDocument();
  });

  it("hides everyone's busy times from ordinary members", async () => {
    renderApp("/scheduling", { as: asCasey });

    expect(await screen.findByRole("region", { name: "Your busy times" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Everyone's busy times" })).not.toBeInTheDocument();
  });
});

describe("scheduling page: weekly busy times", () => {
  async function openWeekly(user: ReturnType<typeof renderApp>["user"]) {
    await user.click(await screen.findByRole("button", { name: "Add busy time" }));
    const dialog = screen.getByRole("dialog", { name: "Add busy time" });
    await user.click(within(dialog).getByRole("radio", { name: "Repeats weekly" }));
    return dialog;
  }

  it("adds a weekly busy time from the pop-up", async () => {
    let sent: RecurringBusyTimeIn | undefined;
    server.use(
      http.post("*/api/v1/recurring-busy-times", async ({ request }) => {
        sent = (await request.json()) as RecurringBusyTimeIn;
        return HttpResponse.json(
          {
            id: 970,
            member: { id: 4, name: "Riley Chen" },
            ...sent,
            time_zone: "America/New_York",
            created_at: "2026-10-28T12:00:00Z",
          },
          { status: 201 },
        );
      }),
    );
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);
    await user.click(within(dialog).getByRole("checkbox", { name: "Thursday" }));
    await user.click(within(dialog).getByRole("checkbox", { name: "Tuesday" }));
    await user.type(within(dialog).getByLabelText("Start time"), "18:00");
    await user.type(within(dialog).getByLabelText("End time"), "21:00");
    const firstDate = within(dialog).getByLabelText("First date");
    await user.clear(firstDate);
    await user.type(firstDate, "2026-11-02");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(sent).toEqual({
      weekdays: [2, 4],
      start_time: "18:00",
      end_time: "21:00",
      starts_on: "2026-11-02",
      ends_on: null,
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows a new weekly busy time in the list, with its days and dates", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);
    for (const day of ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]) {
      await user.click(within(dialog).getByRole("checkbox", { name: day }));
    }
    await user.type(within(dialog).getByLabelText("Start time"), "08:00");
    await user.type(within(dialog).getByLabelText("End time"), "17:00");
    const firstDate = within(dialog).getByLabelText("First date");
    await user.clear(firstDate);
    await user.type(firstDate, "2026-11-02");
    await user.type(within(dialog).getByLabelText("Last date"), "2026-12-18");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(await within(mine()).findByText("Weekdays, 8:00 AM – 5:00 PM")).toBeInTheDocument();
    expect(within(mine()).getByText("Mon, Nov 2, 2026 to Fri, Dec 18, 2026")).toBeInTheDocument();
  });

  it("starts the first date on today", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);

    const now = new Date();
    const today = [now.getFullYear(), now.getMonth() + 1, now.getDate()]
      .map((n) => String(n).padStart(2, "0"))
      .join("-");
    expect(within(dialog).getByLabelText("First date")).toHaveValue(today);
    expect(within(dialog).getByLabelText("Last date")).toHaveValue("");
  });

  it("ties a missing day to the days", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);
    await user.type(within(dialog).getByLabelText("Start time"), "18:00");
    await user.type(within(dialog).getByLabelText("End time"), "21:00");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(within(dialog).getByRole("group", { name: "Days" })).toHaveAccessibleDescription(
      "Pick at least one day.",
    );
    expect(within(dialog).getByRole("checkbox", { name: "Monday" })).toHaveFocus();
  });

  it("won't save a weekly busy time that starts and ends at the same time", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);
    await user.click(within(dialog).getByRole("checkbox", { name: "Monday" }));
    await user.type(within(dialog).getByLabelText("Start time"), "18:00");
    await user.type(within(dialog).getByLabelText("End time"), "18:00");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    const end = within(dialog).getByLabelText("End time");
    expect(end).toHaveAccessibleDescription(
      /The end time has to be different from the start time\.$/,
    );
    expect(end).toHaveFocus();
  });

  it("won't save a last date before the first date", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);
    await user.click(within(dialog).getByRole("checkbox", { name: "Monday" }));
    await user.type(within(dialog).getByLabelText("Start time"), "18:00");
    await user.type(within(dialog).getByLabelText("End time"), "21:00");
    const firstDate = within(dialog).getByLabelText("First date");
    await user.clear(firstDate);
    await user.type(firstDate, "2026-11-10");
    await user.type(within(dialog).getByLabelText("Last date"), "2026-11-01");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(within(dialog).getByLabelText("Last date")).toHaveAccessibleDescription(
      /The last date can't be before the first date\.$/,
    );
  });

  it("allows a weekly busy time that runs past midnight, and says so", async () => {
    const { user } = renderApp("/scheduling", { as: asRiley });

    const dialog = await openWeekly(user);
    await user.click(within(dialog).getByRole("checkbox", { name: "Saturday" }));
    await user.type(within(dialog).getByLabelText("Start time"), "22:00");
    await user.type(within(dialog).getByLabelText("End time"), "02:00");
    await user.click(within(dialog).getByRole("button", { name: "Add busy time" }));

    expect(
      await within(mine()).findByText("Sat, 10:00 PM – 2:00 AM the next day"),
    ).toBeInTheDocument();
  });

  it("lists the band leader's own weekly busy times with a word, not just a color", async () => {
    renderApp("/scheduling", { as: asSam });

    const row = (await within(mine()).findByText("Wed, 6:00 PM – 9:00 PM")).closest("li");
    expect(row).toHaveTextContent("WeeklyWed, 6:00 PM – 9:00 PM");
    expect(row).toHaveTextContent("Starting Wed, Nov 18, 2026");
  });

  it("changes a weekly busy time, starting from what it was", async () => {
    const { user } = renderApp("/scheduling", { as: asSam });

    await user.click(
      await screen.findByRole("button", { name: "Change weekly busy time Wed, 6:00 PM – 9:00 PM" }),
    );
    const dialog = screen.getByRole("dialog", { name: "Change weekly busy time" });
    expect(within(dialog).queryByRole("radio")).not.toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: "Wednesday" })).toBeChecked();
    expect(within(dialog).getByLabelText("Start time")).toHaveValue("18:00");
    expect(within(dialog).getByLabelText("First date")).toHaveValue("2026-11-18");
    await user.click(within(dialog).getByRole("checkbox", { name: "Friday" }));
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    expect(await within(mine()).findByText("Wed, Fri, 6:00 PM – 9:00 PM")).toBeInTheDocument();
  });

  it("deletes a weekly busy time", async () => {
    const { user } = renderApp("/scheduling", { as: asSam });

    await user.click(
      await screen.findByRole("button", { name: "Delete weekly busy time Wed, 6:00 PM – 9:00 PM" }),
    );

    expect(
      await screen.findByText("You haven't marked any busy times, so you count as available."),
    ).toBeInTheDocument();
  });

  it("shows a refused change in the pop-up", async () => {
    server.use(
      http.patch("*/api/v1/recurring-busy-times/:ruleId", () =>
        HttpResponse.json(
          errorBody("not_your_busy_time", "You can only change your own busy times."),
          { status: 403 },
        ),
      ),
    );
    const { user } = renderApp("/scheduling", { as: asSam });

    await user.click(await screen.findByRole("button", { name: /Change weekly busy time/ }));
    const dialog = screen.getByRole("dialog", { name: "Change weekly busy time" });
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "You can only change your own busy times.",
    );
  });
});
