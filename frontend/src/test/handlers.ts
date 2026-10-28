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
  InvitationIn,
  MemberPage,
  MemberProfile,
  MemberProfileUpdate,
  SlotOut,
} from "../api/types";
import {
  allMembers,
  allProfiles,
  blueDoor,
  gigDetails,
  hubCity,
  toListItem,
  undatedDraft,
} from "./fixtures";

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
let profiles = new Map<number, MemberProfile>();

export function resetMockData(): void {
  store = new Map(gigDetails.map((gig) => [gig.id, gig]));
  profiles = new Map(allProfiles.map((profile) => [profile.id, profile]));
}

function actingProfile(request: Request): MemberProfile | undefined {
  return profiles.get(Number(request.headers.get("X-Acting-Member-Id")));
}

/** Phone and email are only for that member, the manager and the band leader. */
function asSeenBy(profile: MemberProfile, actor: MemberProfile | undefined): MemberProfile {
  const seesContact =
    actor && (actor.id === profile.id || actor.is_manager || actor.is_band_leader);
  return seesContact ? profile : { ...profile, email: null, phone: null };
}

const memberNotFound = () =>
  HttpResponse.json(errorBody("member_not_found", "That member doesn't exist."), {
    status: 404,
  });
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

function updateSlot(
  gig: GigDetail,
  slotId: string | readonly string[] | undefined,
  change: (slot: SlotOut) => SlotOut,
): GigDetail | null {
  if (!gig.slots.some((slot) => String(slot.id) === slotId)) return null;
  return saveGig({
    ...gig,
    slots: gig.slots.map((slot) => (String(slot.id) === slotId ? change(slot) : slot)),
  });
}

export const handlers = [
  http.get("*/api/v1/members", () => HttpResponse.json<MemberPage>(page(allMembers))),

  http.get("*/api/v1/members/:memberId", ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const profile = profiles.get(Number(params.memberId));
    return profile
      ? HttpResponse.json(asSeenBy(profile, actingProfile(request)))
      : memberNotFound();
  }),

  http.patch("*/api/v1/members/:memberId", async ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const profile = profiles.get(Number(params.memberId));
    if (!profile) return memberNotFound();
    if (actingProfile(request)?.id !== profile.id) {
      return HttpResponse.json(
        errorBody("not_your_profile", "You can only edit your own profile."),
        { status: 403 },
      );
    }
    const body = (await request.json()) as MemberProfileUpdate;
    const updated: MemberProfile = { ...profile, ...body } as MemberProfile;
    const emailTaken = [...profiles.values()].some(
      (other) =>
        other.id !== profile.id && other.email?.toLowerCase() === body.email?.toLowerCase(),
    );
    if (emailTaken) {
      return HttpResponse.json(
        errorBody("email_taken", "Another member already uses that email address."),
        { status: 409 },
      );
    }
    if (updated.secondary_role !== null && updated.secondary_role === updated.primary_role) {
      return HttpResponse.json(
        errorBody(
          "secondary_same_as_primary",
          "Your secondary instrument has to be different from your primary one.",
        ),
        { status: 409 },
      );
    }
    profiles.set(profile.id, updated);
    return HttpResponse.json(updated);
  }),

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
      pay_cents: body.pay_cents ?? null,
      slots: (body.roles ?? []).map((role, index) => ({
        id: 900 + index,
        role,
        status: "open",
        member: null,
        pay_cents: null,
        responded_at: null,
      })),
      contacts: [],
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

  http.post("*/api/v1/gigs/:gigId/slots/:slotId/invite", async ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const gig = findGig(params.gigId);
    if (!gig) return notFound();
    const body = (await request.json()) as InvitationIn;
    const member = allMembers.find((candidate) => candidate.id === body.member_id);
    const updated = updateSlot(gig, params.slotId, (slot) => ({
      ...slot,
      member: member ? { id: member.id, name: member.name } : null,
      status: "invited",
      pay_cents: body.pay_cents ?? null,
      responded_at: null,
    }));
    return updated
      ? HttpResponse.json(updated)
      : HttpResponse.json(errorBody("slot_not_found", "That slot isn't part of this gig."), {
          status: 404,
        });
  }),

  http.patch("*/api/v1/gigs/:gigId/slots/:slotId", async ({ request, params }) => {
    const refused = requireActingMember(request);
    if (refused) return refused;
    const gig = findGig(params.gigId);
    if (!gig) return notFound();
    const body = (await request.json()) as { pay_cents: number | null };
    const updated = updateSlot(gig, params.slotId, (slot) => ({
      ...slot,
      pay_cents: body.pay_cents,
    }));
    return updated ? HttpResponse.json(updated) : notFound();
  }),

  ...(["accept", "decline"] as const).map((answer) =>
    http.post(`*/api/v1/gigs/:gigId/slots/:slotId/${answer}`, ({ request, params }) => {
      const refused = requireActingMember(request);
      if (refused) return refused;
      const gig = findGig(params.gigId);
      if (!gig) return notFound();
      const updated = updateSlot(gig, params.slotId, (slot) => ({
        ...slot,
        status: answer === "accept" ? "accepted" : "declined",
        responded_at: "2026-10-13T12:00:00Z",
      }));
      return updated ? HttpResponse.json(updated) : notFound();
    }),
  ),
];
