import { expect, type Page } from "@playwright/test";

/** Choose who you are on the login page (the sprint 1 user picker). */
export async function continueAs(page: Page, who: "manager" | string): Promise<void> {
  await page.goto("/login");
  const button =
    who === "manager"
      ? page.getByRole("button", { name: /Continue as manager/ })
      : page.getByRole("button", { name: new RegExp(who) });
  await button.click();
  await expect(page.getByRole("heading", { level: 1, name: "Gigs" })).toBeVisible();
}

/** Switch to someone else from anywhere in the app. */
export async function switchTo(page: Page, who: "manager" | string): Promise<void> {
  await page.getByRole("button", { name: "Switch user" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Roadhouse" })).toBeVisible();
  await continueAs(page, who);
}
