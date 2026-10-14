import { expect, test } from "@playwright/test";

import { continueAs } from "./helpers";

test.describe("Story: the manager sees every upcoming gig in date order with its details", () => {
  test("gigs are listed in date order: The Blue Door (Oct 18) before Hub City Tap (Nov 2)", async ({
    page,
  }) => {
    await continueAs(page, "manager");

    const byDate = page.getByRole("region", { name: "By date" });
    const venues = byDate.getByRole("link");
    await expect(venues.first()).toContainText("The Blue Door");
    await expect(venues.nth(1)).toContainText("Hub City Tap");
  });

  test("opening a gig shows load-in, soundcheck and first set in order, with the venue and contact", async ({
    page,
  }) => {
    await continueAs(page, "manager");

    await page.getByRole("link", { name: /The Blue Door/ }).click();

    const schedule = page.getByRole("region", { name: "Schedule" });
    await expect(schedule.getByRole("listitem")).toHaveText([
      /Load-in\s*6:00 PM/,
      /Soundcheck\s*6:45 PM/,
      /First set\s*8:00 PM/,
      /End\s*11:00 PM/,
    ]);
    await expect(page.getByRole("region", { name: "Details" })).toContainText(
      "123 Main St, Spartanburg, SC",
    );
    await expect(page.getByRole("region", { name: "Contacts" })).toContainText("Pat Lee");
  });
});
