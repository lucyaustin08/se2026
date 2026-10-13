# Decisions

Every choice that had a real alternative. Newest entries at the bottom.

---

## 2026-10-12 — Gig lifecycle: potential, booked, cancelled

**Decision:** A gig has a status of `potential`, `booked`, or `cancelled` (a `StrEnum` in the model layer). Booking and cancelling are named transitions: `POST /api/v1/gigs/{id}/book` and `POST /api/v1/gigs/{id}/cancel`. Only the manager can perform either. The manager can cancel any gig, potential or booked. Cancelled gigs are kept and shown as "Cancelled" to the manager and to assigned members.

**Alternatives considered:**
- `PATCH /gigs/{id}` with a `status` field. Rejected: project conventions require state transitions to be named POST sub-paths.
- Hard-deleting cancelled gigs. Rejected: the product owner wants members to see that a gig was cancelled, and conventions prefer soft deletes.

---

## 2026-10-12 — Draft gigs save with any fields; booking requires all

**Decision:** The manager can save a potential gig with any subset of fields filled in. Booking is refused until the gig has a first set date and time, a venue name and address, a gig type, pay, and at least one contact with a name and at least one way to reach them (phone or email). A refused booking returns `409` with a machine-readable `code`.

**Alternatives considered:**
- Requiring some fields (such as date) to save a draft. Rejected: the team wants managers to capture a lead as soon as it comes in.
- Returning `422` for an incomplete booking. Rejected: the request is well-formed. A business rule refuses it, which is a `409` under project conventions.

**Still open:** whether every lineup slot must be filled before booking (product owner).

---

## 2026-10-12 — Load-in and soundcheck stored as offsets from the first set

**Decision:** Each gig stores the first set time plus load-in and soundcheck offsets before it. The defaults are 2 hours for load-in and 1 hour for soundcheck, and the manager can change either. The displayed clock times are computed, never stored, so moving the first set moves everything with it.

**Alternatives considered:**
- Storing absolute load-in and soundcheck times. Rejected: the product owner wants these times to shift when the set time changes. Absolute times would need extra code to keep them in sync, and project conventions say derived values are computed, not stored.

---

## 2026-10-12 — One primary role per member

**Decision:** Each member has exactly one primary role (for example, lead guitar or bass). Lineup slots are filled from members whose primary role matches.

**Alternatives considered:**
- Multiple roles per member. Not taken for now: the product owner said most members have a specific instrument or role. We'll revisit if the product owner confirms that members sometimes cover other slots (open question).

---

## 2026-10-12 — Overlapping gigs are flagged, not refused

**Decision:** When a gig's times overlap another gig's, the gig still saves and a conflict flag is shown. The conflict is computed from gig times, not stored.

**Alternatives considered:**
- Refusing overlapping gigs with a `409`. Rejected by the product owner.

**Still open:** when a gig ends (which defines the overlap window) and where the flag appears (product owner).

---

## 2026-10-12 — Members see unassigned gigs as date plus "Not assigned"

**Decision:** Members see booked gigs they are not assigned to as a row showing only the date and the text "Not assigned," with the label most prominent. The row cannot be opened, and the server refuses detail requests for that gig from that member. Members never see potential gigs. Gray styling is never the only signal, per the accessibility floor.

**Alternatives considered:**
- Hiding unassigned gigs entirely. Rejected: the product owner wants members to know the band is busy those dates.
- Showing gray styling alone. Rejected: it conveys information by color alone.

---

## 2026-10-12 — Permission refusals return 403

**Decision:** Every permission refusal returns `403` with the standard error envelope and a specific `code`. Examples:
- a member opening an unassigned gig
- a member booking or cancelling a gig
- a member editing someone else's availability

All refusals are raised through one shared exception mapped in a single exception handler. The instructor approved adding `403` to the course status-code conventions.

**Alternatives considered:**
- `404` with a specific `code` and message. Rejected: it reads as "doesn't exist" for gigs the member can plainly see, which is especially confusing on actions like booking.

---

## 2026-10-12 — Sprint 1 identity: user picker, permissions enforced on the server

**Decision:** Sprint 1 has no real login. A user picker in the UI chooses who is "acting," and the frontend sends that user's id with each request. The backend reads it through a dependency and enforces every permission rule, so hiding a button is never the only protection. Members cannot:
- book, edit, or cancel gigs
- edit other members' availability
- see or approve other members' late-arrival requests or availability changes

There is one manager per band.

**Alternatives considered:**
- Building real authentication in sprint 1. Deferred: gigs and members are higher priority, and the picker lets us build and test permission rules now.
- Enforcing permissions only in the frontend. Rejected: anyone could bypass it by calling the API directly.

**Known limitation:** the picker is not secure. It will be replaced by real login (see the invites entry below).

---

## 2026-10-12 — Invites by copied link; email is the login

**Decision:** The manager generates an invite link and copies it to their clipboard to send however they like. The invited member signs up with their email address as their login and chooses their own password.

**Alternatives considered:**
- The app sends invite emails. Rejected: it needs a mail service and a secret outside the course stack.
- Magic-link (passwordless) login. Not taken: it also requires sending email.

**Pending:** passwords need a hashing library, which is not in the stack contract. Check with the instructor before the sprint that builds sign-up.

---

## 2026-10-12 — Late-arrival requests start as pending

**Decision:** A member's late-arrival request is `pending` until the manager acts on it. Only the requesting member and the manager can see it.

**Alternatives considered:**
- Treating a late-arrival request as automatically available or unavailable. Deferred until the product owner gives more detail.

---

## 2026-10-12 — Undated drafts appear in their own "Undated" group

**Decision:** Potential gigs saved without a date are shown in a separate "Undated" group on the manager's gig list rather than mixed into date order.

**Alternatives considered:**
- Sorting undated drafts first. Rejected: it pushes the next real gig down the list.
- Sorting undated drafts last. Rejected: they become easy to forget.

---

## 2026-10-12 — Gig start stored as one UTC timestamp

**Decision:** A gig stores its first set as a single UTC timestamp, `first_set_at`, per the course convention that timestamps are UTC, ISO 8601, with an `_at` suffix. Load-in and soundcheck times are computed from it. A draft may leave it empty, but the date and time are entered together: a draft cannot have a date without a time or a time without a date.

**Alternatives considered:**
- Storing the local date and local set time as separate fields plus a band time zone. Rejected: it departs from the course timestamp convention. Its only advantage was allowing a draft with a time but no date, which the team does not need.

---

## 2026-10-12 — Venue and contact details

**Decision:** A gig has a venue name and a venue address. A gig can have a venue contact and a booking contact, each with a name, phone, and email. All of these are optional on a draft.

**Alternatives considered:**
- A single contact per gig. Rejected: the product owner said the person booking the band is sometimes separate from the venue.
- A separate `Venue` table shared across gigs. Deferred: the Booking feature (tracking venues from first contact) is a later sprint, and it is the natural place to introduce one.

---

## 2026-10-12 — Settings read with the standard library

**Decision:** `app/core/config.py` reads environment variables with `os.environ` into a frozen dataclass.

**Alternatives considered:**
- `pydantic-settings`. Not taken: it is a separate package outside the stack contract, and we only have one setting so far. Revisit (and ask the instructor) if settings grow.

---

## 2026-10-12 — Async API tests use the anyio pytest plugin

**Decision:** Async tests are marked with `pytest.mark.anyio`. The plugin ships with anyio, which httpx and Starlette already depend on.

**Alternatives considered:**
- `pytest-asyncio`. Not taken: it would add a dependency outside the stack contract for no gain.

---

## 2026-10-12 — Validation errors keep the two-field envelope

**Decision:** A `422` returns `{"code": "validation_error", "detail": ...}`, with every failing field and its message folded into the `detail` sentence.

**Alternatives considered:**
- Adding a third field with a structured list of field errors. Not taken: it would break the course-wide envelope. Forms validate on the client first, so the server's `422` is a backstop. Revisit with the instructor if the frontend needs per-field server errors.

---

## 2026-10-12 — Health check touches the database

**Decision:** `GET /api/v1/health` runs `SELECT 1` and reports `ok` only if the database answers.

**Alternatives considered:**
- A health check that always returns `ok`. Not taken: Docker Compose healthchecks should fail when the app can't reach its database.

---

## 2026-10-12 — Navigation sections and placeholder pages

**Decision:** The app has six top-level sections in this order: Dashboard, Gigs, Scheduling, Songs & Setlists, Members, Booking. Sections without a feature yet show a placeholder page. The list lives in one place (`src/navigation.ts`), which both the navigation and the routes read.

**Alternatives considered:**
- Adding each section only when its feature is built. Not taken: the product owner suggested these tabs, and a fixed shell lets the team see the whole app's shape from the start.

---

## 2026-10-12 — Frontend served by unprivileged nginx, API proxied through it

**Decision:** The frontend image serves the built app with `nginxinc/nginx-unprivileged` on port 8080, and nginx forwards `/api/` to the backend container. In development, Vite's dev server does the same forwarding. The frontend therefore always calls relative `/api/...` URLs and needs no API base URL setting.

**Alternatives considered:**
- The stock `nginx` image. Not taken: it starts as root, and the stack contract requires non-root containers.
- Having the browser call the backend on its own port. Not taken: it would need CORS configuration and a per-environment API URL.

---

## 2026-10-12 — Frontend dependencies installed by a bootstrap script

**Decision:** `frontend/scripts/bootstrap-deps.sh` installs the initial dependencies with pnpm, pinning only the majors the constitution fixes (React 19, Vite 8, Vitest 4, TypeScript 5, ESLint 9, Tailwind 4) and taking the current release of everything else.

**Alternatives considered:**
- Hand-writing version ranges in `package.json`. Not taken: several packages had major releases recently enough that hand-picked ranges risked pinning an outdated major.

---

## 2026-10-12 — Generated API types deferred to the first feature that calls the API

**Decision:** The `openapi-typescript` and `openapi-fetch` pipeline, plus TanStack Query and MSW, are set up together with the gigs feature, which is the first frontend code that calls the API.

**Alternatives considered:**
- Setting them up in the app shell. Not taken: with no API calls yet, there would be nothing to test them against.

---

## 2026-10-13 — Acting member sent in the `X-Acting-Member-Id` header

**Decision:** The user picker stores the chosen member's id, and the frontend sends it on every request in an `X-Acting-Member-Id` header. One dependency, `get_acting_member`, turns it into a `Member`. A missing header returns `403 acting_member_required`, and an unknown id returns `403 unknown_acting_member`.

**Alternatives considered:**
- `401 Unauthorized` for a missing header. More correct in HTTP terms, but `401` is not in the course status-code list. The instructor approved only `403`. Revisit when real login replaces the picker.
- A query parameter. Not taken: it would appear in every URL and in server logs.

`GET /api/v1/members` does not require the header, because the picker needs the list before anyone has chosen.

---

## 2026-10-13 — Lineup is edited by replacing it as a whole

**Decision:** `PATCH /api/v1/gigs/{id}` accepts a `lineup` list of `{slot, member_id}`, and when present, it replaces every assignment. Each gig type has fixed slots (Duo: rhythm guitar/vocals and lead guitar; Full Band: those plus bass, drums and specialty). A member can only fill the slot matching their primary role, can fill only one slot per gig, and each slot holds one member. These are `409`s with the codes `slot_not_in_lineup`, `member_role_mismatch`, `member_in_two_slots`, `duplicate_slot` and `gig_type_required`.

**Alternatives considered:**
- A separate `/gigs/{id}/assignments` sub-resource with one call per slot. Not taken: the lineup form saves all slots at once, and partial failures would leave half a lineup.
- Silently removing assignments when the gig type changes. Not taken: it would lose data without warning. Changing the type while members hold slots the new type lacks is refused (`409 lineup_not_in_gig_type`) unless the new lineup is sent in the same request.

**Trio:** only its two fixed slots can be filled until the product owner says how the third slot works.

---

## 2026-10-13 — A lineup entry naming a member who doesn't exist is a 409

**Decision:** `409 unknown_member`.

**Alternatives considered:**
- `404`. Not taken: in our conventions, `404` means the resource in the URL doesn't exist, and here the gig does.
- `422`. Not taken: the request is well-formed, and a business rule refuses it.

---

## 2026-10-13 — What members can see

**Decision:**
- Members see only booked gigs.
- A potential gig returns `404 gig_not_found` to a member, the same answer as a gig that doesn't exist, so members can't tell potential gigs exist.
- Booked gigs a member isn't on appear in the list as `restricted` rows with only id, status and date.
- A member's search only matches gigs they're assigned to, because matching on venue or contact names would otherwise reveal a restricted gig's details.
- Members never see pay, while the product owner's answer on pay visibility is pending.

**Alternatives considered:**
- Returning `403` for a member opening a potential gig. Not taken: it would confirm the gig exists.

---

## 2026-10-13 — `missing_for_booking` is computed and returned with each gig

**Decision:** Gig details include `missing_for_booking`, a list of plain-language names for whatever the gig still needs before it can be booked. It's computed by the same function that enforces the booking rule, so the screen and the rule can't disagree. Members get an empty list.

**Alternatives considered:**
- Repeating the rule in the frontend. Not taken: two copies of a business rule drift apart.

---

## 2026-10-13 — A booked gig can be edited only while it stays complete

**Decision:** Editing a booked gig is allowed, but an edit that would remove anything booking requires is refused with `409 gig_incomplete`, and nothing is saved.

**Alternatives considered:**
- Locking booked gigs. Not taken: times and contacts change after booking.
- Allowing anything. Not taken: members would see a booked gig with no time or address.

---

## 2026-10-13 — Clearing a time offset resets it to the default

**Decision:** In `PATCH`, sending `null` for `load_in_offset_minutes` or `soundcheck_offset_minutes` resets it to 120 or 60 minutes. Omitted fields are unchanged, and `null` clears every other field.

**Alternatives considered:**
- Rejecting `null` for offsets. Not taken: "back to the default" is the natural meaning of clearing a field the form pre-fills.

---

## 2026-10-13 — Sample band seeded by an environment flag

**Decision:** `python -m app.seed` adds a made-up band (a manager and one member per role) and three gigs, but only when `SEED_SAMPLE_DATA` is true and the database has no members. Docker Compose turns it on, and the backend container runs it after migrations.

**Alternatives considered:**
- A data migration. Not taken: sample data would end up in every environment, including future production.

---

## 2026-10-13 — `Location` headers are relative paths

**Decision:** `201` responses set `Location: /api/v1/gigs/{id}`.

**Alternatives considered:**
- An absolute URL. Not taken: behind nginx the backend sees the wrong host and port, so the absolute URL would be wrong.

---

## 2026-10-13 — Unique-constraint names include every column

**Decision:** The naming convention for unique constraints is `uq_<table>_<all columns>`.

**Alternatives considered:**
- The earlier `uq_<table>_<first column>`. Changed: `gig_assignments` has two unique constraints starting with `gig_id`, which would have had the same name.

---

## Open questions noticed while building (product owner)

- **Past gigs.** The stories say "upcoming gigs," but nobody has said what happens to a gig after its date. The list currently shows every gig in date order, past ones included.
- **Load-in after soundcheck.** Nothing stops a manager from setting load-in later than soundcheck. Should that be refused?
