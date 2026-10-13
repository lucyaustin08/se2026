/**
 * Default MSW handlers: one per API endpoint, answering like the real backend does for the
 * fixture data. Tests override them with `server.use(...)` for other cases.
 */
import { http, HttpResponse } from "msw";

import type {
  ErrorResponse,
  GigCreate,
  GigDetail,
  GigPage,
  GigUpdate,
  MemberPage,
} from "../api/types";
import { allMembers, blueDoor, gigDetails, hubCity, toListItem, undatedDraft } from "./fixtures";

export function errorBody(code: string, detail: string): ErrorResponse {
  return { code, detail };
}

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 100 };
}

function requireActingMember(request: Request) {
  if (!request.headers.get("X-Acting-Member-Id")) {
    return HttpResponse.json(
      errorBody("acting_member_required", "Choose who you are before using the app."),
      { status: 403 },
    );
  }
  return null;
}

// The mock server's own copy of the data, so a refetch after a change returns the change,
// as the real backend would. Reset after every test (see test_setup.ts).
let store = new Map<number, GigDetail>();

export function resetMockData(): void {
  store = new Map(gigDetails.map((gig) => [gig.id, gig]));
}
resetMockData();

/** Save a gig into the mock server, for tests that override a handler. */
export function saveGig(gig: GigDetail): GigDetail {
  store.set(gig.id, gig);
  return gig;
}

function findGig(id: string | readonly string[] | undefined): GigDetail | undefined {
  return store.get(Number(id));
}

const notFound = () =>
  HttpResponse.json(errorBody("gig_not_found", "That gig doesn't exist."), { status: 404 });

export const handlers = [
  http.get("*/api/v1/members", () => HttpResponse.json<MemberPage>(page(allMembers))),

  http.get("*/api/v1/gigs", ({ request }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const hasDate = new URL(request.url).searchParams.get("has_date");
    const items =
      hasDate === "false" ? [undatedDraft] : [toListItem(blueDoor), toListItem(hubCity)];
    return HttpResponse.json<GigPage>(page(items));
  }),

  http.post("*/api/v1/gigs", async ({ request }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const body = (await request.json()) as GigCreate;
    const created: GigDetail = {
      ...hubCity,
      id: 99,
      first_set_at: body.first_set_at ?? null,
      venue_name: body.venue_name ?? null,
      venue_address: body.venue_address ?? null,
      gig_type: body.gig_type ?? null,
      pay_cents: body.pay_cents ?? null,
      lineup: [],
    };
    return HttpResponse.json(saveGig(created), {
      status: 201,
      headers: { Location: "/api/v1/gigs/99" },
    });
  }),

  http.get("*/api/v1/gigs/:gigId", ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const gig = findGig(params.gigId);
    return gig ? HttpResponse.json(gig) : notFound();
  }),

  http.patch("*/api/v1/gigs/:gigId", async ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const gig = findGig(params.gigId);
    if (!gig) return notFound();
    const body = (await request.json()) as GigUpdate;
    const updated: GigDetail = { ...gig };
    if (body.venue_name !== undefined) updated.venue_name = body.venue_name;
    if (body.pay_cents !== undefined) updated.pay_cents = body.pay_cents;
    if (body.lineup) {
      updated.lineup = gig.lineup.map((slot) => {
        const entry = body.lineup?.find((assignment) => assignment.slot === slot.slot);
        const member = allMembers.find((candidate) => candidate.id === entry?.member_id);
        return { slot: slot.slot, member: member ? { id: member.id, name: member.name } : null };
      });
    }
    return HttpResponse.json(saveGig(updated));
  }),

  http.post("*/api/v1/gigs/:gigId/book", ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const gig = findGig(params.gigId);
    if (!gig) return notFound();
    if (gig.missing_for_booking.length > 0) {
      return HttpResponse.json(
        errorBody(
          "gig_incomplete",
          `This gig can't be booked until it has: ${gig.missing_for_booking.join(", ")}.`,
        ),
        { status: 409 },
      );
    }
    return HttpResponse.json(saveGig({ ...gig, status: "booked" }));
  }),
];
