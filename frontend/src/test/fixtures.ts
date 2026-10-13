import type { GigDetail, GigListItem, MemberRead } from "../api/types";
import type { ActingMember } from "../session";

export const managerMember: MemberRead = {
  id: 1,
  name: "Jordan Avery",
  primary_role: null,
  is_manager: true,
};
export const sam: MemberRead = {
  id: 2,
  name: "Sam Rivera",
  primary_role: "rhythm_guitar_vocals",
  is_manager: false,
};
export const casey: MemberRead = {
  id: 3,
  name: "Casey Morgan",
  primary_role: "lead_guitar",
  is_manager: false,
};
export const riley: MemberRead = {
  id: 4,
  name: "Riley Chen",
  primary_role: "bass",
  is_manager: false,
};

export const allMembers = [managerMember, sam, casey, riley];

export const asManager: ActingMember = { id: 1, name: "Jordan Avery", isManager: true };
export const asSam: ActingMember = { id: 2, name: "Sam Rivera", isManager: false };
export const asRiley: ActingMember = { id: 4, name: "Riley Chen", isManager: false };

/** A booked duo at The Blue Door: 8:00 PM Eastern on Oct 18, 2026, Sam and Casey playing. */
export const blueDoor: GigDetail = {
  id: 10,
  status: "booked",
  first_set_at: "2026-10-19T00:00:00Z",
  load_in_at: "2026-10-18T22:00:00Z",
  soundcheck_at: "2026-10-18T22:45:00Z",
  load_in_offset_minutes: 120,
  soundcheck_offset_minutes: 75,
  venue_name: "The Blue Door",
  venue_address: "123 Main St, Spartanburg, SC",
  gig_type: "duo",
  pay_cents: 40000,
  venue_contact: { name: "Pat Lee", phone: "555-0142", email: null },
  booking_contact: null,
  lineup: [
    { slot: "rhythm_guitar_vocals", member: { id: 2, name: "Sam Rivera" } },
    { slot: "lead_guitar", member: { id: 3, name: "Casey Morgan" } },
  ],
  missing_for_booking: [],
  created_at: "2026-10-01T12:00:00Z",
};

/** A potential full-band gig at Hub City Tap that is missing an address, pay and contact. */
export const hubCity: GigDetail = {
  id: 11,
  status: "potential",
  first_set_at: "2026-11-03T01:00:00Z",
  load_in_at: "2026-11-02T23:00:00Z",
  soundcheck_at: "2026-11-03T00:00:00Z",
  load_in_offset_minutes: 120,
  soundcheck_offset_minutes: 60,
  venue_name: "Hub City Tap",
  venue_address: null,
  gig_type: "full_band",
  pay_cents: null,
  venue_contact: null,
  booking_contact: null,
  lineup: [
    { slot: "rhythm_guitar_vocals", member: null },
    { slot: "lead_guitar", member: null },
    { slot: "bass", member: null },
    { slot: "drums", member: null },
    { slot: "specialty", member: null },
  ],
  missing_for_booking: [
    "venue address",
    "pay",
    "a contact with a name and a phone number or email",
  ],
  created_at: "2026-10-02T12:00:00Z",
};

/** A potential duo with everything booking needs. */
export const readyToBook: GigDetail = {
  ...blueDoor,
  id: 12,
  status: "potential",
  venue_name: "The Grange",
  lineup: [
    { slot: "rhythm_guitar_vocals", member: null },
    { slot: "lead_guitar", member: null },
  ],
};

export const undatedDraft: GigListItem = {
  id: 13,
  status: "potential",
  first_set_at: null,
  venue_name: "Wedding inquiry",
  gig_type: null,
  restricted: false,
};

export function toListItem(gig: GigDetail): GigListItem {
  return {
    id: gig.id,
    status: gig.status,
    first_set_at: gig.first_set_at,
    venue_name: gig.venue_name,
    gig_type: gig.gig_type,
    restricted: false,
  };
}

export function restricted(gig: GigDetail): GigListItem {
  return { ...toListItem(gig), venue_name: null, gig_type: null, restricted: true };
}

export const gigDetails: GigDetail[] = [blueDoor, hubCity, readyToBook];
