import { expect, test } from "@playwright/test";

import { continueAs } from "./helpers";

test.describe("Story: a member sees the gigs they're playing, and only the date of others", () => {
  test("a member on the lineup opens the gig and sees their own role and pay", async ({ page }) => {
    // Casey is an ordinary member. Sam, the band leader, sees every gig in full.
    await continueAs(page, "Casey Morgan");

    await page.getByRole("link", { name: /The Blue Door/ }).click();

    const invitation = page.getByRole("region", { name: "Your invitation" });
    await expect(invitation).toContainText("Lead guitar");
    await expect(invitation).toContainText("Your pay: $200.00");
    await expect(page.getByRole("link", { name: "Edit details" })).toHaveCount(0);
  });

  test("a gig the member isn't on shows only its date and 'Not assigned', and doesn't open", async ({
    page,
  }) => {
    await continueAs(page, "Riley Chen");

    const byDate = page.getByRole("region", { name: "By date" });
    const row = byDate.getByRole("listitem").filter({ hasText: "Not assigned" }).first();
    await expect(row).toContainText("Sun, Oct 18, 2026");
    await expect(row).not.toContainText("The Blue Door");
    await expect(row.getByRole("link")).toHaveCount(0);
  });
});
