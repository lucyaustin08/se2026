/**
 * Each player's calendar color. Only the calendar uses these, and always with a name or
 * initials, so color is never the only way to tell members apart.
 */
import type { MemberRead } from "./api/types";

// Full class names, so Tailwind sees them when it scans the code.
const MEMBER_FILLS = [
  "bg-member-1",
  "bg-member-2",
  "bg-member-3",
  "bg-member-4",
  "bg-member-5",
  "bg-member-6",
  "bg-member-7",
  "bg-member-8",
] as const;

/**
 * Members keep the same color as long as the band doesn't change: players are numbered in
 * the order they joined (by id), and the manager, who doesn't play, has none.
 */
export function memberFills(members: MemberRead[]): Map<number, string> {
  const players = members.filter((m) => !m.is_manager).sort((a, b) => a.id - b.id);
  return new Map(players.map((m, i) => [m.id, MEMBER_FILLS[i % MEMBER_FILLS.length]]));
}

export const UNKNOWN_MEMBER_FILL = "bg-paper";
