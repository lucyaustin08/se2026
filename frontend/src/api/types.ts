/** Short names for the generated API types. Nothing here is hand-written: it all comes from
 * the backend's OpenAPI schema (see `pnpm gen:api`). */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type BusyPeriod = Schemas["BusyPeriod"];
export type BusyPeriods = Schemas["BusyPeriods"];
export type BusyTimeIn = Schemas["BusyTimeIn"];
export type BusyTimeOut = Schemas["BusyTimeOut"];
export type BusyTimePage = Schemas["BusyTimePage"];
export type Conflict = Schemas["Conflict"];
export type ContactIn = Schemas["ContactIn"];
export type ContactLabel = Schemas["ContactLabel"];
export type ContactOut = Schemas["ContactOut"];
export type ErrorResponse = Schemas["ErrorResponse"];
export type GigCreate = Schemas["GigCreate"];
export type GigAvailability = Schemas["GigAvailability"];
export type GigDetail = Schemas["GigDetail"];
export type GigListItem = Schemas["GigListItem"];
export type GigPage = Schemas["GigPage"];
export type GigStatus = Schemas["GigStatus"];
export type GigUpdate = Schemas["GigUpdate"];
export type InvitationIn = Schemas["InvitationIn"];
export type InvitationStatus = Schemas["InvitationStatus"];
export type LineupSize = Schemas["LineupSize"];
export type MemberPage = Schemas["MemberPage"];
export type MemberProfile = Schemas["MemberProfile"];
export type MemberProfileUpdate = Schemas["MemberProfileUpdate"];
export type MemberRead = Schemas["MemberRead"];
export type PlayerAvailability = Schemas["PlayerAvailability"];
export type PracticeCreate = Schemas["PracticeCreate"];
export type PracticeOut = Schemas["PracticeOut"];
export type PracticePage = Schemas["PracticePage"];
export type PracticeSuggestions = Schemas["PracticeSuggestions"];
export type RecurringBusyTimeIn = Schemas["RecurringBusyTimeIn"];
export type RecurringBusyTimeOut = Schemas["RecurringBusyTimeOut"];
export type RecurringBusyTimePage = Schemas["RecurringBusyTimePage"];
export type Role = Schemas["Role"];
export type SlotOut = Schemas["SlotOut"];
export type SuggestedTime = Schemas["SuggestedTime"];
export type SlotStatus = Schemas["SlotStatus"];
