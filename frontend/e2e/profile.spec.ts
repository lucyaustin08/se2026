import { expect, test } from "@playwright/test";

import { continueAs } from "./helpers";

test.describe("Story: a member keeps their own profile up to date", () => {
  test("a member adds a phone number and a secondary instrument", async ({ page }) => {
    await continueAs(page, "Taylor Brooks");

    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Profile" })
      .click();
    await expect(page.getByRole("heading", { level: 1, name: "Profile" })).toBeVisible();
    await expect(page.getByText("Roles are fixed and can't be changed.")).toBeVisible();

    await page.getByRole("button", { name: "Edit profile" }).click();
    await page.getByLabel("Phone").fill("555-0144");
    await page.getByLabel("Secondary instrument").selectOption({ label: "Bass" });
    await page.getByRole("button", { name: "Save profile" }).click();

    await expect(page.getByRole("button", { name: "Edit profile" })).toBeVisible();
    await expect(page.getByText("555-0144")).toBeVisible();
    await expect(page.getByText("Bass", { exact: true })).toBeVisible();
  });
});
