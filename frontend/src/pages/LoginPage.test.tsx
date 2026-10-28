import { screen, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { getActingMember } from "../session";
import { casey, managerMember, riley, sam } from "../test/fixtures";
import { errorBody } from "../test/handlers";
import { renderApp } from "../test/render";
import { server } from "../test/server";

describe("login page", () => {
  it("shows a loading message while the band loads", async () => {
    server.use(http.get("*/api/v1/members", () => delay("infinite")));

    renderApp("/login");

    expect(await screen.findByRole("status")).toHaveTextContent("Loading the band…");
  });

  it("shows an error with a retry that works", async () => {
    server.use(
      http.get(
        "*/api/v1/members",
        () => HttpResponse.json(errorBody("internal_error", "Something broke."), { status: 500 }),
        { once: true },
      ),
    );
    const { user } = renderApp("/login");

    expect(await screen.findByRole("alert")).toHaveTextContent("Something broke.");

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByRole("button", { name: /Continue as manager/ })).toBeInTheDocument();
  });

  it("says so when there are no members yet", async () => {
    server.use(
      http.get("*/api/v1/members", () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 100 }),
      ),
    );

    renderApp("/login");

    expect(await screen.findByText("No band members have been added yet.")).toBeInTheDocument();
  });

  it("offers the manager, the band leader, and each member with their role", async () => {
    renderApp("/login");

    expect(
      await screen.findByRole("button", { name: /Continue as manager\s*Jordan Avery/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /Continue as band leader\s*Sam Rivera · Rhythm guitar \/ vocals/,
      }),
    ).toBeInTheDocument();
    const members = screen.getByRole("region", { name: "Continue as a member" });
    expect(within(members).getByRole("button", { name: /Riley Chen\s*Bass/ })).toBeInTheDocument();
    expect(within(members).queryByRole("button", { name: /Sam Rivera/ })).not.toBeInTheDocument();
  });

  it("explains when no band leader has been set up", async () => {
    server.use(
      http.get("*/api/v1/members", () =>
        HttpResponse.json({ items: [managerMember, riley], total: 2, page: 1, page_size: 100 }),
      ),
    );

    renderApp("/login");

    expect(await screen.findByText("No band leader has been set up yet.")).toBeInTheDocument();
  });

  it("explains when no manager has been set up", async () => {
    server.use(
      http.get("*/api/v1/members", () =>
        HttpResponse.json({ items: [sam, casey], total: 2, page: 1, page_size: 100 }),
      ),
    );

    renderApp("/login");

    expect(await screen.findByText("No manager has been set up yet.")).toBeInTheDocument();
  });

  it("continuing as the manager opens the gigs page as the manager", async () => {
    const { user } = renderApp("/login");

    await user.click(await screen.findByRole("button", { name: /Continue as manager/ }));

    expect(await screen.findByRole("heading", { level: 1, name: "Gigs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add gig" })).toBeInTheDocument();
    expect(getActingMember()).toEqual({
      id: managerMember.id,
      name: "Jordan Avery",
      isManager: true,
      isBandLeader: false,
    });
  });

  it("continuing as the band leader opens the gigs page as the band leader", async () => {
    const { user } = renderApp("/login");

    await user.click(await screen.findByRole("button", { name: /Continue as band leader/ }));

    expect(await screen.findByRole("heading", { level: 1, name: "Gigs" })).toBeInTheDocument();
    expect(screen.getByText(/Using Roadhouse as/)).toHaveTextContent(
      "Using Roadhouse as Sam Rivera (band leader)",
    );
    expect(screen.queryByRole("link", { name: "Add gig" })).not.toBeInTheDocument();
    expect(getActingMember()).toEqual({
      id: sam.id,
      name: "Sam Rivera",
      isManager: false,
      isBandLeader: true,
    });
  });

  it("continuing as a member opens the gigs page as that member", async () => {
    const { user } = renderApp("/login");

    await user.click(await screen.findByRole("button", { name: /Casey Morgan/ }));

    expect(await screen.findByRole("heading", { level: 1, name: "Gigs" })).toBeInTheDocument();
    expect(screen.getByText(/Using Roadhouse as/)).toHaveTextContent(
      "Using Roadhouse as Casey Morgan (band member)",
    );
    expect(screen.queryByRole("link", { name: "Add gig" })).not.toBeInTheDocument();
  });
});
