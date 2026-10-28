import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { BusyTimeIn } from "../api/types";
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

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

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
    expect(within(dialog).getByLabelText("Start date")).toHaveFocus();
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
    expect(screen.queryByRole("region", { name: "Your busy times" })).not.toBeInTheDocument();
  });

  it("shows the band leader their own busy times and everyone's", async () => {
    renderApp("/scheduling", { as: asSam });

    expect(await screen.findByRole("region", { name: "Your busy times" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Everyone's busy times" })).toBeInTheDocument();
  });

  it("says when nobody has marked busy times", async () => {
    server.use(http.get("*/api/v1/busy-times", () => HttpResponse.json(emptyPage)));

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
