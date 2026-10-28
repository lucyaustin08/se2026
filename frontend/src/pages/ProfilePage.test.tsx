import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { getActingMember } from "../session";
import { asCasey, asManager, asSam } from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("profile page", () => {
  it("shows a loading message while the profile loads", async () => {
    server.use(http.get("*/api/v1/members/:memberId", () => delay("infinite")));

    renderApp("/profile", { as: asCasey });

    expect(await screen.findByRole("status")).toHaveTextContent("Loading your profile…");
  });

  it("shows an error with a retry that works", async () => {
    server.use(
      http.get(
        "*/api/v1/members/:memberId",
        () => HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/profile", { as: asCasey });

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("Casey Morgan", { selector: "p" })).toBeInTheDocument();
  });

  it("shows a member their details, instruments and fixed role", async () => {
    renderApp("/profile", { as: asCasey });

    expect(await screen.findByRole("heading", { level: 1, name: "Profile" })).toBeInTheDocument();
    expect(await screen.findByText("Casey Morgan", { selector: "p" })).toBeInTheDocument();
    const details = screen.getByText("Phone").closest("dl") as HTMLElement;
    expect(details).toHaveTextContent("Phone555-0102");
    expect(details).toHaveTextContent("Emailcasey@example.com");
    expect(details).toHaveTextContent("Primary instrumentLead guitar");
    expect(details).toHaveTextContent("Secondary instrumentNot set");
    expect(screen.getByText("Member", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Roles are fixed and can't be changed.")).toBeInTheDocument();
  });

  it("labels the band leader by role", async () => {
    renderApp("/profile", { as: asSam });
    expect(await screen.findByText("Band leader", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Bass")).toBeInTheDocument();
  });

  it("labels the manager by role", async () => {
    renderApp("/profile", { as: asManager });
    expect(await screen.findByText("Manager", { selector: "span" })).toBeInTheDocument();
  });

  it("saves edits and shows them, keeping the header's name in step", async () => {
    const { user } = renderApp("/profile", { as: asCasey });

    await user.click(await screen.findByRole("button", { name: "Edit profile" }));
    const name = screen.getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "Casey Morgan-Lee");
    const phone = screen.getByLabelText("Phone");
    await user.clear(phone);
    await user.type(phone, "555-0199");
    await user.selectOptions(screen.getByLabelText("Secondary instrument"), "Drums");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByRole("button", { name: "Edit profile" })).toBeInTheDocument();
    expect(screen.getByText("Casey Morgan-Lee", { selector: "p" })).toBeInTheDocument();
    const details = screen.getByText("Phone").closest("dl") as HTMLElement;
    expect(details).toHaveTextContent("Phone555-0199");
    expect(details).toHaveTextContent("Secondary instrumentDrums");
    expect(screen.getByText(/Using Roadhouse as/)).toHaveTextContent("Casey Morgan-Lee");
    expect(getActingMember()?.name).toBe("Casey Morgan-Lee");
  });

  it("cancelling leaves the profile unchanged", async () => {
    const { user } = renderApp("/profile", { as: asCasey });

    await user.click(await screen.findByRole("button", { name: "Edit profile" }));
    await user.clear(screen.getByLabelText("Name"));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByText("Casey Morgan", { selector: "p" })).toBeInTheDocument();
  });

  const EMAIL_HINT = "Only the manager and band leader see it.";

  it.each([
    { field: "Name", value: "", description: "Enter your name." },
    { field: "Email", value: "", description: `${EMAIL_HINT} Enter your email address.` },
    {
      field: "Email",
      value: "casey",
      description: `${EMAIL_HINT} Enter an email address like name@example.com.`,
    },
  ])("ties '$description' to the $field field", async ({ field, value, description }) => {
    const { user } = renderApp("/profile", { as: asCasey });

    await user.click(await screen.findByRole("button", { name: "Edit profile" }));
    const input = screen.getByLabelText(field);
    await user.clear(input);
    if (value) await user.type(input, value);
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(input).toHaveAccessibleDescription(description);
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveFocus();
  });

  it("won't let the secondary instrument match the primary", async () => {
    const { user } = renderApp("/profile", { as: asCasey });

    await user.click(await screen.findByRole("button", { name: "Edit profile" }));
    const secondary = screen.getByLabelText("Secondary instrument");
    await user.selectOptions(secondary, "Lead guitar");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(secondary).toHaveAccessibleDescription(
      "Optional. Something else you can cover. Choose a different instrument from your primary one.",
    );
    expect(secondary).toHaveFocus();
  });

  it("shows the server's 'email taken' refusal on the email field", async () => {
    const { user } = renderApp("/profile", { as: asCasey });

    await user.click(await screen.findByRole("button", { name: "Edit profile" }));
    const email = screen.getByLabelText("Email");
    await user.clear(email);
    await user.type(email, "sam@example.com");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(
      await within(email.parentElement as HTMLElement).findByText(
        "Another member already uses that email address.",
      ),
    ).toBeInTheDocument();
    expect(email).toHaveAccessibleDescription(
      `${EMAIL_HINT} Another member already uses that email address.`,
    );
    expect(screen.getByRole("button", { name: "Save profile" })).toBeInTheDocument();
  });

  it("shows other save failures above the form", async () => {
    server.use(
      http.patch("*/api/v1/members/:memberId", () =>
        HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
      ),
    );
    const { user } = renderApp("/profile", { as: asCasey });

    await user.click(await screen.findByRole("button", { name: "Edit profile" }));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");
  });
});
