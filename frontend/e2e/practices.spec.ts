import { expect, test } from "@playwright/test";

import { continueAs, switchTo } from "./helpers";

// A unique date per run (in 2030, clear of every other story's gigs).
const stamp = Date.now();
const day = new Date(Date.UTC(2030, 0, 1) + (Math.floor(stamp / 60_000) % 300) * 86_400_000)
  .toISOString()
  .slice(0, 10);
const location = `Practice room ${stamp}`;

test.describe("Story: the band leader schedules a practice and invited members answer", () => {
  test("the band leader invites a member to practice, and the member says they'll be there", async ({
    page,
  }) => {
    await continueAs(page, "Sam Rivera");
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Scheduling" })
      .click();
    await page.getByRole("button", { name: "Schedule practice" }).click();
    const dialog = page.getByRole("dialog", { name: "Schedule practice" });
    await dialog.getByLabel("Date").fill(day);
    await dialog.getByLabel("Start time").fill("18:00");
    await dialog.getByLabel("Location").fill(location);
    await dialog.getByRole("checkbox", { name: /Taylor Brooks/ }).check();
    await dialog.getByRole("button", { name: "Schedule practice" }).click();
    await expect(dialog).toHaveCount(0);

    const card = page.getByRole("listitem").filter({ hasText: location });
    await expect(card.getByRole("list", { name: "Who's invited" })).toContainText(
      "Taylor Brooks Invited",
    );

    await switchTo(page, "Taylor Brooks");
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Scheduling" })
      .click();
    const mine = page.getByRole("listitem").filter({ hasText: location });
    await mine.getByRole("button", { name: "I'll be there" }).click();
    await expect(mine).toContainText("Your answer:Coming");
  });
});
