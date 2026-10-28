import { expect, test } from "@playwright/test";

import { continueAs, switchTo } from "./helpers";

// A unique date per run (in 2029, clear of the booking story's dates), so the story can be
// re-run against the same database.
const stamp = Date.now();
const day = new Date(Date.UTC(2029, 0, 1) + (Math.floor(stamp / 60_000) % 300) * 86_400_000)
  .toISOString()
  .slice(0, 10);
const venue = `Busy Night ${stamp}`;

test.describe("Story: a member marks when they're busy, and the manager sees it when inviting", () => {
  test("a member adds a busy time, and they show as busy in the gig's invite list", async ({
    page,
  }) => {
    // Riley marks the evening as busy.
    await continueAs(page, "Riley Chen");
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Scheduling" })
      .click();
    await page.getByRole("button", { name: "Add busy time" }).click();
    const dialog = page.getByRole("dialog", { name: "Add busy time" });
    await dialog.getByLabel("Start date").fill(day);
    await dialog.getByLabel("Start time").fill("18:00");
    await dialog.getByLabel("End time").fill("23:30");
    await dialog.getByRole("button", { name: "Add busy time" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(
      page.getByRole("region", { name: "Your busy times" }).getByText(/6:00 PM – 11:30 PM/),
    ).toBeVisible();

    // The manager adds a gig that evening and goes to invite a bass player.
    await switchTo(page, "manager");
    await page.getByRole("link", { name: "Add gig" }).click();
    await page.getByLabel("Date", { exact: true }).fill(day);
    await page.getByLabel("First set time", { exact: true }).fill("20:00");
    await page.getByLabel("Venue name", { exact: true }).fill(venue);
    await page.getByRole("checkbox", { name: "Bass" }).check();
    await page.getByRole("button", { name: "Save gig" }).click();
    await expect(page.getByRole("heading", { level: 1, name: venue })).toBeVisible();

    const invite = page.getByLabel("Invite for Bass");
    await expect(invite.getByRole("option", { name: "Riley Chen · Busy" })).toHaveCount(1);
  });
});
