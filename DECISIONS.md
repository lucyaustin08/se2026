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

> **Updated 2026-10-13:** a member's primary role now only orders the invite list. Anyone can be invited to any slot as a backup.

**Decision:** Each member has exactly one primary role (for example, lead guitar or bass). Lineup slots are filled from members whose primary role matches.

**Alternatives considered:**
- Multiple roles per member. Not taken for now: the product owner said most members have a specific instrument or role. We'll revisit if the product owner confirms that members sometimes cover other slots (open question).

---

## 2026-10-12 — Overlapping gigs are flagged, not refused

> **Replaced 2026-10-13:** the product owner now says a member can't confirm two overlapping gigs. See "No member can accept two overlapping gigs."

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

> **Replaced 2026-10-13:** each gig now has a list of contacts. See "Contacts are a list on each gig."

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

> **Replaced 2026-10-13:** fixed gig types and direct assignment are gone. See "Each gig lists its own roles" and "Members join a gig by accepting an invitation."

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


---

## 2026-10-13 — Generated API types are not committed

**Decision:** `frontend/src/api/schema.d.ts` is generated from the backend's OpenAPI schema and git-ignored. CI exports the schema from the backend and generates the types before type-checking. The frontend Docker build does the same in an extra build stage. Developers run `pnpm gen:api:live` against a running backend (see `frontend/README.md`).

**Alternatives considered:**
- Committing `schema.d.ts` and failing CI when it's stale. Not taken: every backend change would need a second, generated commit, and forgetting it breaks the build for everyone.

This replaces the earlier entry that deferred the type pipeline.

---

## 2026-10-13 — How the frontend talks to the API

**Decision:**
- One `openapi-fetch` client (`src/api/client.ts`) with a middleware that adds `X-Acting-Member-Id` to every request.
- `unwrap()` turns error responses into an `ApiError` carrying the status and `code`, so TanStack Query treats them as failures.
- Queries don't retry `4xx` answers, which won't change on a retry.
- The client calls `globalThis.fetch` on every request rather than capturing it at startup, so MSW can intercept it in tests.

**Alternatives considered:**
- Checking `error` at every call site. Not taken: it's repetitive, and it's easy to forget a check.

---

## 2026-10-13 — Who's acting is kept in sessionStorage

**Decision:** The picker's choice is kept in memory and mirrored to `sessionStorage`, so it survives a reload but not a new tab. It holds only id, name and whether the person is the manager. The server re-checks every permission.

**Alternatives considered:**
- `localStorage`. Not taken: two people sharing a laptop would stay "signed in" as each other across tabs.
- A global state library. Not allowed by the stack contract, and a small React context is enough.

---

## 2026-10-13 — Gig times entered in the browser's local time

**Decision:** The form's date and time inputs are in the browser's time zone. The frontend converts them to UTC before sending, and converts UTC back to local time for display. This is correct as long as everyone in the band is in the same time zone as the gigs.

**Alternatives considered:**
- Storing a time zone per gig or per band. Deferred: no one has asked for out-of-town gigs in another time zone.

---

## 2026-10-13 — Gig list loads up to 100 gigs per group

**Decision:** The gig page asks for up to 100 dated gigs and 100 undated drafts (the maximum page size) and says so when there are more. There are no page controls yet.

**Alternatives considered:**
- Previous/next page controls now. Deferred until a band actually has more than 100 gigs.

---

## 2026-10-13 — Product owner answers (round 3)

Recorded as given, for reference:
- **Pay:** a gig has a set total, visible to the band leader. The band leader decides each member's pay.
- **Lineup:** solo, duo, trio, quartet or full band. The leader picks the instrumentation for each gig.
- **Overlap:** a member can't confirm two gigs at the same time. A morning gig and an evening gig are fine.
- **Invitations:** the manager creates a draft with the instrumentation and asks members. A member marked busy can still be invited and decide for themselves. If someone can't make it, the manager asks a backup. Keep it personal rather than fully automated.
- **Band leader:** a gig can't go ahead without the band leader.
- **Length:** gigs usually last two to three hours. Members stay the whole show. They may ask to arrive late, but not to leave early.
- **Contacts:** varies by gig. Store any number of contacts, with names, phones, emails and other details.

---

## 2026-10-13 — Team readings of those answers (confirm with the product owner)

- The **band manager and band leader are different people.** The manager organizes and doesn't play. The leader plays and must be on every gig.
- **"Confirm" means a member accepts an invitation.** Only then are they on the gig.
- **A gig can't be booked until every invited member has accepted**, including the band leader.
- The band leader is **invited like anyone else**. There's no automatic slot, but booking is refused until the leader has accepted one.

---

## 2026-10-13 — Each gig lists its own roles

**Decision:** The manager picks which roles a gig needs (rhythm guitar/vocals, lead guitar, bass, drums, specialty). Each becomes a slot. The size label (solo, duo, trio, quartet; five or more is a full band) is computed from the number of slots. A role can appear only once per gig for now.

**Alternatives considered:**
- Keeping fixed gig types with fixed slots. Replaced: the product owner wants flexible instrumentation.
- Storing the size label. Not taken: it's derived from the slots, so it is computed.

**For the product owner:** can a gig ever need two of the same role, or roles beyond these five (keys, fiddle)?

---

## 2026-10-13 — Members join a gig by accepting an invitation

**Decision:** Each slot has a status: `open`, `invited`, `accepted` or `declined`.
- The manager invites a member: `POST /gigs/{id}/slots/{slot_id}/invite`, with that member's pay.
- The member answers: `POST …/accept` or `POST …/decline`.
- After a decline, or while an invitation is still pending, the manager can invite someone else to the same slot. An accepted slot can't be re-invited (`409 slot_already_filled`).
- Any member can be invited to any slot as a backup. The invite list shows members who usually play that role first.
- The manager can't be invited, because they don't play (`409 manager_cannot_play`).
- Invitations only happen while the gig is potential.

**Alternatives considered:**
- Automatically asking every member who plays the role. Not taken: the product owner wants the manager to stay personally in the loop.
- Refusing to invite members marked busy. Not taken: the product owner wants them asked anyway, so they can decide.

---

## 2026-10-13 — Pay: the gig total and each member's share

**Decision:** The gig keeps its total (`pay_cents`), which only the manager sees. Each slot has the pay for that member, set when inviting or changed later with `PATCH /gigs/{id}/slots/{slot_id}` (there's no screen for changing it yet). A member sees only their own pay.

**Alternatives considered:**
- Showing members the total or everyone's pay. Not taken: the product owner said the total is for the band leader.

**For the product owner:** should the app warn when members' pay adds up to more than the total?

---

## 2026-10-13 — No member can accept two overlapping gigs

> **Replaced 2026-10-27:** a member is now busy from soundcheck, not load-in. See "A member is busy from soundcheck to the end."

**Decision:** A gig has a length (`performance_minutes`, default 180) after the first set, so it has a computed end time. A member is busy from **load-in to the end**.
- Accepting an invitation is refused (`409 overlapping_gig`) if that window overlaps another gig the member already accepted.
- Moving a gig's time so that it overlaps another gig an accepted member is on is also refused.
- Cancelled and undated gigs never count.

**Alternatives considered:**
- Flagging but allowing overlaps (the earlier decision). Replaced by the product owner's answer.
- Counting only from the first set. Not taken: members have to be there for load-in.

---

## 2026-10-13 — Contacts are a list on each gig

**Decision:** A gig has any number of contacts, each with a type (venue, booking, other), name, phone, email and notes. Booking needs at least one contact with a name and a phone or email.

**Alternatives considered:**
- Contacts shared by venue, so they're reused next time. Deferred to the Booking feature, which will track venues.

---

## 2026-10-13 — What members can see (updated)

**Decision:** Members see:
- booked gigs they're on
- potential gigs they've been invited to or have accepted
- other booked gigs as "Not assigned" rows

A potential gig a member isn't invited to (or has declined) returns `404`, the same as a gig that doesn't exist.

---

## 2026-10-13 — Existing data carried through migration 0002

**Decision:** Migration 0002 turns old assignments into pending invitations and old contact fields into contacts, rather than dropping them.

**Alternatives considered:**
- Editing migration 0001 in place. Not taken: anyone who already ran 0001 locally would end up with a database that doesn't match.

---

## Open questions (product owner)

- **Past gigs.** The stories say "upcoming gigs," but nobody has said what happens to a gig after its date. The list currently shows every gig in date order, past ones included.
- **Load-in after soundcheck.** Nothing stops a manager from setting load-in later than soundcheck. Should that be refused?
- **Late arrivals:** members can ask to arrive late. The design is decided (pending until the manager answers), but it isn't built yet.
- **Backing out:** can a member who accepted later withdraw? Can the manager remove an accepted member?

---

## 2026-10-14 — GitHub Codespaces for running the app without Docker

**Decision:** The repo includes a dev container (`.devcontainer/`). Opening it in GitHub Codespaces gives each teammate a cloud machine with uv, Python 3.14, Node 24 and pnpm, and every dependency installed from the lock files. `bash scripts/dev.sh` runs migrations, loads the sample band, generates the API types, and starts the backend (port 8000) and the Vite dev server (port 5173).
- CI builds the same dev container and checks that `scripts/dev.sh` serves both the app and the API, so the setup can't silently break.
- Vite allows the `*.app.github.dev` hostname Codespaces uses.

Docker Compose stays exactly as it was. It's part of the stack contract, and CI still builds and tests the production images with it. Codespaces only removes the need for Docker on teammates' own computers.

**Alternatives considered:**
- Running `docker compose` inside the codespace. Not taken: it's slower to start, and code changes would need an image rebuild instead of live reloading.
- Asking everyone to install Docker Desktop. Not taken: several teammates work only in the browser with GitHub and Copilot.

**Pending:** confirm with the instructor that a dev container is fine as an addition to the stack.

---

## 2026-10-14 — Acceptance tests with Playwright, one per user story

**Decision:** `frontend/e2e/` holds Playwright tests named after the user stories they accept:
- the manager sees gigs in date order with their details
- a member sees their own gigs, and only the date of others
- the manager adds a gig, invites the band leader, the leader accepts, and the manager books it

They run in CI against the real app in Docker Compose, in Eastern time, one at a time (they share a database). Playwright's HTML report and a summary table are saved on every run.

They cover happy paths only, per the testing standard. Refusals and edge cases stay in the faster unit, API and page tests.

**Alternatives considered:**
- Cucumber-style `.feature` files. Not taken: they aren't in the course stack. Playwright is, and naming each test after its story keeps the mapping clear.
- Running against MSW mocks. Not taken: acceptance tests should prove the real frontend, backend and database work together.

---

## 2026-10-27 — A member is busy from soundcheck to the end

**Decision:** For the overlap rule, a member on a gig is busy from **soundcheck to the end**, not from load-in. The product owner said every member must be able to be there "by soundcheck at the latest."
- Accepting an invitation is refused (`409 overlapping_gig`) if this gig's soundcheck-to-end window overlaps the same window of another gig the member already accepted.
- A gig that ends exactly when another gig's soundcheck starts is not an overlap.
- Editing a gig re-checks accepted members when the first set, soundcheck offset or length changes. Changing only the load-in offset no longer triggers the check, because load-in no longer counts.
- The same window will decide whether a member is free for a gig when availability is added.

**Alternatives considered:**
- Keeping load-in to end (the 2026-10-13 rule). Replaced: the product owner only requires members to arrive by soundcheck.
- Using a different window for "can accept two gigs" and "is free for a gig." Not taken: the product owner gave one rule, and two windows would confuse members and the manager.
