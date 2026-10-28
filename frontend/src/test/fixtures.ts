import type { GigDetail, GigListItem, MemberRead, SlotOut } from "../api/types";
import type { ActingMember } from "../session";

export const managerMember: MemberRead = {
  id: 1,
  name: "Jordan Avery",
  primary_role: null,
  is_manager: true,
  is_band_leader: false,
};
export const sam: MemberRead = {
  id: 2,
  name: "Sam Rivera",
  primary_role: "rhythm_guitar_vocals",
  is_manager: false,
  is_band_leader: true,
};
export const casey: MemberRead = {
  id: 3,
  name: "Casey Morgan",
  primary_role: "lead_guitar",
  is_manager: false,
  is_band_leader: false,
};
export const riley: MemberRead = {
  id: 4,
  name: "Riley Chen",
  primary_role: "bass",
  is_manager: false,
  is_band_leader: false,
};

export const allMembers = [managerMember, sam, casey, riley];

export const asManager: ActingMember = {
  id: 1,
  name: "Jordan Avery",
  isManager: true,
  isBandLeader: false,
};
/** Sam is the band leader. */
export const asSam: ActingMember = {
  id: 2,
  name: "Sam Rivera",
  isManager: false,
  isBandLeader: true,
};
export const asCasey: ActingMember = {
  id: 3,
  name: "Casey Morgan",
  isManager: false,
  isBandLeader: false,
};
export const asRiley: ActingMember = {
  id: 4,
  name: "Riley Chen",
  isManager: false,
  isBandLeader: false,
};

function slot(
  id: number,
  role: SlotOut["role"],
  member: MemberRead | null,
  status: SlotOut["status"],
  pay_cents: number | null = null,
): SlotOut {
  return {
    id,
    role,
    status,
    member: member ? { id: member.id, name: member.name } : null,
    pay_cents,
    responded_at: status === "accepted" || status === "declined" ? "2026-10-05T16:00:00Z" : null,
  };
}

/** A booked duo at The Blue Door: 8:00 PM Eastern on Oct 18, 2026, as the manager sees it. */
export const blueDoor: GigDetail = {
  id: 10,
  status: "booked",
  first_set_at: "2026-10-19T00:00:00Z",
  load_in_at: "2026-10-18T22:00:00Z",
  soundcheck_at: "2026-10-18T22:45:00Z",
  end_at: "2026-10-19T03:00:00Z",
  load_in_offset_minutes: 120,
  soundcheck_offset_minutes: 75,
  performance_minutes: 180,
  venue_name: "The Blue Door",
  venue_address: "123 Main St, Spartanburg, SC",
  lineup_size: "duo",
  pay_cents: 40000,
  slots: [
    slot(101, "rhythm_guitar_vocals", sam, "accepted", 20000),
    slot(102, "lead_guitar", casey, "accepted", 20000),
  ],
  contacts: [
    {
      id: 201,
      label: "venue",
      name: "Pat Lee",
      phone: "555-0142",
      email: null,
      notes: "Load in through the alley door.",
    },
  ],
  my_slot_id: null,
  missing_for_booking: [],
  created_at: "2026-10-01T12:00:00Z",
};

/** The same gig as Sam, the band leader, sees it: everything, plus his own slot. */
export const blueDoorForSam: GigDetail = { ...blueDoor, my_slot_id: 101 };

/** The same gig as Casey, an ordinary member, sees it: no total, no contacts, only her pay. */
export const blueDoorForCasey: GigDetail = {
  ...blueDoor,
  pay_cents: null,
  slots: [
    slot(101, "rhythm_guitar_vocals", sam, "accepted", null),
    slot(102, "lead_guitar", casey, "accepted", 20000),
  ],
  contacts: [],
  my_slot_id: 102,
};

/** A potential full-band gig at Hub City Tap with invitations in every state. */
export const hubCity: GigDetail = {
  id: 11,
  status: "potential",
  first_set_at: "2026-11-03T01:00:00Z",
  load_in_at: "2026-11-02T23:00:00Z",
  soundcheck_at: "2026-11-03T00:00:00Z",
  end_at: "2026-11-03T04:00:00Z",
  load_in_offset_minutes: 120,
  soundcheck_offset_minutes: 60,
  performance_minutes: 180,
  venue_name: "Hub City Tap",
  venue_address: null,
  lineup_size: "quartet",
  pay_cents: null,
  slots: [
    slot(111, "rhythm_guitar_vocals", sam, "invited"),
    slot(112, "lead_guitar", casey, "accepted", 15000),
    slot(113, "bass", riley, "declined"),
    slot(114, "drums", null, "open"),
  ],
  contacts: [],
  my_slot_id: null,
  missing_for_booking: [
    "venue address",
    "pay",
    "a contact with a name and a phone number or email",
    "an accepted member for rhythm guitar/vocals",
    "an accepted member for bass",
    "an accepted member for drums",
    "the band leader, accepted into the lineup",
  ],
  created_at: "2026-10-02T12:00:00Z",
};

/** A potential duo where everyone has accepted. */
export const readyToBook: GigDetail = {
  ...blueDoor,
  id: 12,
  status: "potential",
  venue_name: "The Grange",
};

/** A potential gig Riley has been invited to, as Riley sees it. */
export const rileyInvitation: GigDetail = {
  ...readyToBook,
  id: 14,
  venue_name: "Morgan's Pub",
  pay_cents: null,
  slots: [
    slot(141, "rhythm_guitar_vocals", sam, "accepted", null),
    slot(142, "bass", riley, "invited", 15000),
  ],
  my_slot_id: 142,
  missing_for_booking: [],
};

export const undatedDraft: GigListItem = {
  id: 13,
  status: "potential",
  first_set_at: null,
  venue_name: "Wedding inquiry",
  lineup_size: null,
  restricted: false,
  my_slot_status: null,
};

export function toListItem(gig: GigDetail): GigListItem {
  return {
    id: gig.id,
    status: gig.status,
    first_set_at: gig.first_set_at,
    venue_name: gig.venue_name,
    lineup_size: gig.lineup_size,
    restricted: false,
    my_slot_status: gig.slots.find((s) => s.id === gig.my_slot_id)?.status ?? null,
  };
}

export function restricted(gig: GigDetail): GigListItem {
  return {
    ...toListItem(gig),
    venue_name: null,
    lineup_size: null,
    restricted: true,
    my_slot_status: null,
  };
}

export const gigDetails: GigDetail[] = [blueDoor, hubCity, readyToBook, rileyInvitation];
