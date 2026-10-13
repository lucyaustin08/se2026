/** Short names for the generated API types. Nothing here is hand-written: it all comes from
 * the backend's OpenAPI schema (see `pnpm gen:api`). */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ContactIn = Schemas["ContactIn"];
export type ContactLabel = Schemas["ContactLabel"];
export type ContactOut = Schemas["ContactOut"];
export type ErrorResponse = Schemas["ErrorResponse"];
export type GigCreate = Schemas["GigCreate"];
export type GigDetail = Schemas["GigDetail"];
export type GigListItem = Schemas["GigListItem"];
export type GigPage = Schemas["GigPage"];
export type GigStatus = Schemas["GigStatus"];
export type GigUpdate = Schemas["GigUpdate"];
export type InvitationIn = Schemas["InvitationIn"];
export type LineupSize = Schemas["LineupSize"];
export type MemberPage = Schemas["MemberPage"];
export type MemberRead = Schemas["MemberRead"];
export type Role = Schemas["Role"];
export type SlotOut = Schemas["SlotOut"];
export type SlotStatus = Schemas["SlotStatus"];
