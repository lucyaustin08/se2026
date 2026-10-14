import { expect, test } from "@playwright/test";

import { continueAs, switchTo } from "./helpers";

// A unique venue and date per run, so the story can be re-run against the same database
// without the band leader being double-booked by an earlier run.
const stamp = Date.now();
const venue = `Acceptance Hall ${stamp}`;
const day = new Date(Date.UTC(2028, 0, 1) + (Math.floor(stamp / 60_000) % 2000) * 86_400_000)
  .toISOString()
  .slice(0, 10);

test.describe("Story: the manager adds a gig, invites the band, and books it", () => {
  test("add a potential gig, invite the band leader, they accept, then the manager books it", async ({
    page,
  }) => {
    // The manager adds a potential gig with everything booking needs.
    await continueAs(page, "manager");
    await page.getByRole("link", { name: "Add gig" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Add a gig" })).toBeVisible();
    await page.getByLabel("Date", { exact: true }).fill(day);
    await page.getByLabel("First set time", { exact: true }).fill("20:00");
    await page.getByLabel("Venue name", { exact: true }).fill(venue);
    await page.getByLabel("Venue address", { exact: true }).fill("1 Test Street, Spartanburg, SC");
    await page.getByLabel("Total pay for the gig (USD)", { exact: true }).fill("300");
    await page.getByRole("checkbox", { name: "Rhythm guitar / vocals" }).check();
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("Contact 1 name", { exact: true }).fill("Pat Lee");
    await page.getByLabel("Contact 1 phone", { exact: true }).fill("555-0142");
    await page.getByRole("button", { name: "Save gig" }).click();

    await expect(page.getByRole("heading", { level: 1, name: venue })).toBeVisible();
    await expect(page.getByText("Potential", { exact: true })).toBeVisible();
    const gigUrl = page.url();

    // The manager invites the band leader with their pay.
    await page
      .getByLabel("Invite for Rhythm guitar / vocals")
      .selectOption({ label: "Sam Rivera" });
    await page.getByLabel("Pay for Rhythm guitar / vocals (USD)").fill("300");
    await page.getByRole("button", { name: "Send invitation" }).click();
    await expect(page.getByText("Sam Rivera · Invited, waiting for an answer")).toBeVisible();

    // The band leader accepts.
    await switchTo(page, "Sam Rivera");
    await page.goto(gigUrl);
    const invitation = page.getByRole("region", { name: "Your invitation" });
    await expect(invitation).toContainText("Your pay: $300.00");
    await invitation.getByRole("button", { name: "Accept" }).click();
    await expect(invitation.getByText("Accepted", { exact: true })).toBeVisible();

    // The manager books the gig.
    await switchTo(page, "manager");
    await page.goto(gigUrl);
    const booking = page.getByRole("region", { name: "Booking" });
    await expect(booking).toContainText("Everyone has accepted");
    await booking.getByRole("button", { name: "Book gig" }).click();
    await expect(page.getByText("Booked", { exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Booking" })).toHaveCount(0);
  });
});
