# Decisions

Every choice that had a real alternative. Newest entries at the bottom.

---

## 2026-10-12 — Gig lifecycle: potential, booked, cancelled

> **Updated 2026-10-28:** the band leader can also book, and will be able to cancel. See "The band leader runs gigs too."

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

> **Updated 2026-10-28:** the band leader also sees the total and everyone's pay, and can change a member's pay. See "The band leader's permissions."

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

## 2026-10-21 — Design foundation: "Gig Poster" look, fonts stored in the repo

**Decision:** The team picked the "Gig Poster" direction from three mood boards. Its colors, fonts and status colors are defined once in `frontend/src/styles/index.css`. The existing color names (`brand-*`, `gray-*`, `ink-900`) now point at the new palette, so current pages change without edits. New code uses the named colors (`paper`, `ink`, `poster-red`, `mustard`, `navy`, `status-*`) and `font-display` for headings.

The fonts (Anton for headings, Archivo for text) are stored as files in `frontend/public/fonts`, with their SIL Open Font License files.

**Alternatives considered:**
- Font packages such as `@fontsource/anton`. Not taken: they add dependencies outside the stack contract, which needs instructor approval. The font files are the same either way.
- A Google Fonts link. Not taken: the app would depend on an outside service every time it loads.

**Still to do:** the paper background, square corners and headings in Anton, when the shared layout and components are restyled.
## 2026-10-27 — A member is busy from soundcheck to the end

**Decision:** For the overlap rule, a member on a gig is busy from **soundcheck to the end**, not from load-in. The product owner said every member must be able to be there "by soundcheck at the latest."
- Accepting an invitation is refused (`409 overlapping_gig`) if this gig's soundcheck-to-end window overlaps the same window of another gig the member already accepted.
- A gig that ends exactly when another gig's soundcheck starts is not an overlap.
- Editing a gig re-checks accepted members when the first set, soundcheck offset or length changes. Changing only the load-in offset no longer triggers the check, because load-in no longer counts.
- The same window will decide whether a member is free for a gig when availability is added.

**Alternatives considered:**
- Keeping load-in to end (the 2026-10-13 rule). Replaced: the product owner only requires members to arrive by soundcheck.
- Using a different window for "can accept two gigs" and "is free for a gig." Not taken: the product owner gave one rule, and two windows would confuse members and the manager.

---

## 2026-10-28 — The band leader's permissions

> **Updated 2026-10-28:** the band leader can now also add, edit, book and invite. See "The band leader runs gigs too."

**Decision:** The manager and the band leader are two different people (confirmed by the instructor). Both "run the band," and one check, `runs_the_band()` in `app/services/permissions.py`, decides what they can do beyond an ordinary member. The frontend mirrors it with `runsTheBand()` in `src/session.tsx` to decide what to show, but the server enforces every rule.

What the band leader can do now:
- See every gig in full, like the manager: pending gigs they aren't invited to, and booked gigs they aren't on, with no "Not assigned" rows.
- See the gig's total pay and everyone's pay. The product owner said the total is "viewable by the band leader" and that the band leader decides each member's pay.
- Change a member's pay (`PATCH /gigs/{id}/slots/{slot_id}`). A refusal is `403 manager_or_band_leader_only`. There's still no screen for changing pay, so this is API only for now.
- See venue contacts. Per the product owner's sprint 1 feedback, contacts are private to the people managing the booking. Ordinary members, even on the gig, now get an empty list and no Contacts section.

What stays with the manager only: adding, editing, booking and cancelling gigs, and sending invitations (`403 manager_only`).

The band leader still plays: they have their own slot on a gig and accept or decline their own invitation.

To come with their features, per the team's follow-up to the product owner: seeing everyone's availability, revoking an acceptance and inviting a backup, scheduling practices, and seeing member emails. Each should use `runs_the_band()`.

The user picker has a "Continue as band leader" section. A choice saved in `sessionStorage` before this change has no `isBandLeader`, so it's ignored and the person picks again.

**Alternatives considered:**
- Treating the band leader as an ordinary member (the sprint 1 behavior). Replaced: the product owner gives the band leader pay and contact access.
- Letting the band leader do everything the manager does. Not taken: the product owner and instructor describe two roles, and booking stays with the manager.
- Checking `is_manager or is_band_leader` at each call site. Not taken: the same rule will be needed by availability, revoking and practices, and copies drift apart.

---

## 2026-10-28 — The band leader runs gigs too

**Decision:** The band leader can do everything the manager does with gigs: add and edit gigs (including choosing the roles), book them, and invite members, including picking a backup. Every one of these uses `runs_the_band()`, so a refusal is always `403 manager_or_band_leader_only`, and the `manager_only` code is no longer used. Cancelling isn't built yet. When it is, it uses the same check.

The only difference left between them is that the band leader plays: they have their own slot and answer their own invitation, and the manager can't be invited (`409 manager_cannot_play`).

The team decided this after the earlier entry kept these actions with the manager. That earlier choice was made without asking the team.

**Alternatives considered:**
- Keeping adding, editing, booking and inviting with the manager (the earlier entry). Replaced: the product owner said gigs are "confirmed and booked by the band leader/manager," and that the band leader determines the instrumentation for each performance.

**For the product owner (sprint review):** confirm that the band leader and manager have the same gig powers.

---

## 2026-10-28 — Member profiles

**Decision:** Every user has a Profile tab showing their name, phone, email, primary instrument, optional secondary instrument and role. They can edit everything except the role.
- `GET /members/{id}` returns a profile to anyone in the band. `email` and `phone` are `null` unless the reader is that member, the manager or the band leader.
- `PATCH /members/{id}` only works on your own profile (`403 not_your_profile`, even for the manager and band leader). Omitted fields are unchanged, and `null` clears the phone or an instrument. Name and email can't be cleared.
- **Roles are fixed.** There is one manager and one band leader, and nobody can change roles, not even the manager. The update schema forbids extra fields, so sending `is_manager` or `is_band_leader` is a `422`.
- **The secondary instrument can't match the primary** (`409 secondary_same_as_primary`). The check uses the saved primary when only the secondary is sent, so swapping the two in one edit works.
- **Emails are unique without regard to case** (`409 email_taken`), because the email will be the login.
- The `Email` and `Phone` field types moved to `app/schemas/fields.py`, because gig and member schemas both use them and importing one from the other made a cycle.

**Alternatives considered:**
- Letting the manager change roles (the backlog's first wording). Not taken: the team decided roles are fixed.
- A `422` for a secondary instrument matching the primary. Not taken: the rule compares against the saved primary, so it's a business rule (`409`), not request validation.
- Letting the manager edit other members' profiles. Not taken: the product owner said members edit their own.

**For the product owner (sprint review):** if the band ever changes band leaders, should the manager be able to reassign the role in the app?

---

## 2026-10-28 — One-off busy times

**Decision:** Members enter when they're **busy**, as the product owner asked. This stage adds one-off busy times (recurring ones come later). A busy time is a start and an end in UTC, and it may run over several days.
- `GET /busy-times`: the manager and band leader see everyone's, filtered by `member_id` if they like. Members see only their own, and asking for someone else's is `403 availability_private`. `ends_after` and `starts_before` pick a date range, and they must carry a time zone (`422` otherwise).
- `POST /busy-times` adds one for whoever is acting. `PATCH /busy-times/{id}` takes both times again. `DELETE /busy-times/{id}` returns `204`. Only the owner can change or delete one (`403 not_your_busy_time`, even for the manager and band leader).
- An end at or before the start is a `422`: it's checked from the request alone.
- No reason is asked for, so there's no `q` on the list: a busy time has no text to search.
- The manager doesn't play, so the Scheduling page doesn't offer them busy times of their own.

**Alternatives considered:**
- Soft-deleting busy times. Not taken: a deleted busy time has no history worth keeping, and every availability check would have to skip deleted rows. This is a deliberate exception to the soft-delete convention.
- Members entering when they're available. Replaced: the product owner chose busy times.
- Nesting them under `/members/{id}/busy-times`. Not taken: the calendar needs everyone's busy times in a date range in one request.

---

## 2026-10-28 — Who's busy when inviting

**Decision:** `GET /gigs/{id}/availability` (manager or band leader) lists every player with whether they're busy during the gig's **soundcheck-to-end** window, and why: a busy time that overlaps it, or another accepted gig whose soundcheck-to-end window overlaps it. It's computed on every request, never stored. A busy time that ends exactly at soundcheck doesn't count. A player with no busy times is available. For a gig with no date, the window is `null` and nobody is marked busy.

The invite list marks busy players "Name · Busy" and, once one is chosen, says why. A busy player can still be invited, as the product owner asked. The list now has three groups: players whose primary instrument is the role, then players whose secondary instrument is the role ("Also plays …"), then everyone else as backups.

The overlap check that was private to the gig service is now `busy_window()`, so both services use the same window.

**Alternatives considered:**
- Hiding busy players or refusing to invite them. Not taken: the product owner wants them asked, so they can decide.

---

## 2026-10-28 — One-time practices

**Decision:** The manager and band leader schedule one-time practices and invite any group of players. The product owner said weekly practices aren't a priority, so there are none.
- A practice has a start, a length (default 3 hours, from 30 minutes to 12 hours), and an optional location and notes. Its end is computed, never stored.
- Invitations are `invited`, `accepted` or `declined`. A member answers once (`409 invitation_not_pending`), the same as gigs. The manager can't be invited, because they don't play (`409 manager_cannot_play`). If the band leader schedules a practice and invites themselves, their own invitation starts as accepted.
- The manager and band leader see every practice and everyone's answers. Members see only the practices they're invited to, with their own answer. A practice a member isn't invited to returns `404`, like a gig they can't see.
- **Conflicts with gigs:**
  - A practice that overlaps a booked or pending gig's soundcheck-to-end window is refused (`409 practice_overlaps_gig`, naming the gig).
  - A practice on the same day as a gig, in the band's local time, is refused with `409 practice_same_day_as_gig` unless the request sets `confirm_same_day`. The app shows that as a warning with "Schedule anyway" and "Change the time."
  - Cancelled gigs never count.
- **The band's time zone** is one constant, `America/New_York`, in `app/services/band_time.py`, using Python's built-in `zoneinfo`. It's needed for "same day," and recurring busy times will use it too.

**Alternatives considered:**
- Weekly practices. Not built: the product owner said they aren't a priority right now.
- Only booked gigs blocking practices (the product owner's words). Extended by the team to pending gigs too, so the band never turns down a gig because a practice is already scheduled at that time.
- A separate "check" endpoint before saving. Not taken: one `POST` that refuses with a specific code, then is resent with `confirm_same_day`, keeps the rule in one place.
- Using the gig's load-in for overlaps. Not taken: the rest of the app treats a gig as running from soundcheck to the end.

**Not built yet:** changing or cancelling a practice. Neither is in this sprint's stories.

---

## 2026-10-28 — The band calendar

**Decision:** The Scheduling tab opens with a calendar of gigs, practices and busy times, built by the team with no calendar library (the stack contract allows none).
- **Views:** a month view (whole Sunday-to-Saturday weeks) and a week view. The chosen day and view are kept in the address (`?date=2026-11-12&view=month`), so Back works and a day can be linked to.
- **Picking a day:** clicking a day lists its details underneath. In the grid, only the chosen day is in the tab order, and the arrow keys move between days.
- **On phones:** each day shows one lettered mark per entry (G, P, B) instead of text.
- **Who sees what:** the same rules as everywhere else. The manager and band leader see all gigs, practices and busy times. Members see their gigs (others' booked gigs as "Not assigned"), the practices they're invited to, and only their own busy times. Cancelled gigs aren't shown.
- **Telling kinds apart:** gigs have a solid poster-red edge, practices a solid navy edge, and busy times a dashed ink edge on the member's color. The day's details name each kind in words.
- **Dates:** everything is in the browser's local time. The gig list gained `first_set_after` and `first_set_before` filters, so the calendar asks only for the dates it shows. Each kind loads at most 100 entries per view.

**Alternatives considered:**
- A calendar library such as FullCalendar. Not taken: it's outside the stack contract.
- An hour-by-hour week grid. Not taken: an agenda per day is easier to read on a phone and to use with a screen reader, and the band's days rarely have more than a few entries.

---

## 2026-10-28 — Member colors on the calendar

**Decision:** The team chose to give each player a color on the calendar, as an exception to `DESIGN.md`'s Three Inks Rule that applies **only to the calendar**. Fonts, text colors and everything else stay as they are. There are eight soft, print-style fills (`member-1` to `member-8` in `index.css`). Text on them is always ink, and they always come with the member's initials or name. Players get colors in the order they joined, so a member keeps theirs.

**Alternatives considered:**
- Only the three inks plus line patterns. Not taken by the team: too few combinations to tell five or more players apart at a glance.
- Initials only. Not taken: the backlog asks for color-coded members.

---

## 2026-10-28 — Finding a practice time

**Decision:** `GET /practices/suggestions` (manager or band leader) suggests practice times. The scheduler chooses who's invited (`member_ids`, repeated), the length, and the hours of the day to consider (`earliest`, `latest`, local clock times, default 5:00 to 11:00 PM). It's computed on every request, never stored.
- **Days searched:** 7 to 21 days from today in the band's time zone, because the product owner said practices are usually planned one to three weeks ahead.
- **Times tried:** starts every 30 minutes, built from the local wall clock with `zoneinfo`, so 5:00 PM stays 5:00 PM across daylight saving changes.
- **Never suggested:** a time that overlaps a booked or pending gig's soundcheck-to-end window.
- **Who can come:** an invitee can't come if one of their busy times, or another practice they haven't declined, overlaps.
- **Ranking:** each day offers its best time (most invitees free, then earliest), and days are ranked the same way. Each suggestion names who can't come, and flags a gig earlier or later that day.
- **In the app:** "Find a time" sits in the Schedule practice pop-up and shows the top eight. "Use this time" fills in the date and start time. It doesn't schedule anything, so the scheduler still decides, and the same-day warning still applies.
- **Order of checks:** the hours must leave room for the practice (`422`). An unknown member is a `409`, as when scheduling.

**Alternatives considered:**
- Every possible time, not one per day. Not taken: dozens of near-identical half-hour slots on one evening bury the choice between days, which is the real decision.
- Only suggesting times when everyone can come. Not taken: the product owner said a smaller group can still meet, and asked for the times that work for the most people.
- Recurring busy times aren't built yet. When they are, they join the same per-member check (`_member_busy_periods`), so suggestions and the invite list stay in step.

---

## 2026-10-28 — PostgreSQL instead of SQLite

**Decision:** The app, its tests and every environment now use PostgreSQL 17. SQLite support is removed. The instructor suggested moving to a database server that handles time zones and daylight saving itself, and left the choice of server to the team, which chose PostgreSQL. This departs from the stack contract's "SQLite by default," using the PostgreSQL option the contract already names (`postgresql+psycopg://`).
- **Why:** PostgreSQL stores times as real moments (`timestamp with time zone`), not text, and does time math in the database, including `AT TIME ZONE 'America/New_York'` with daylight saving. Recurring busy times need that. It's also what a band using the app for real gigs would run on.
- **Driver:** `psycopg[binary]`, so no PostgreSQL client library has to be installed anywhere. Every connection works in UTC (`-c timezone=UTC`), whatever zone the server runs in.
- **Docker Compose** runs a `db` service (`postgres:17`). Its password comes from a `.env` file that's never committed, and Compose stops with a clear message if it's missing. The database isn't published on a host port. The SQLite volume is gone.
- **Codespaces:** the dev container installs PostgreSQL, and `scripts/dev.sh` starts it through `scripts/start-postgres.sh`, which creates the `roadhouse` user and database if they're missing. That user's password ("roadhouse") only exists inside each codespace.
- **Tests** run on PostgreSQL only, at `TEST_DATABASE_URL`, in their own `roadhouse_test` database. Tables are built from the models once per run, and every table is emptied (`TRUNCATE … RESTART IDENTITY`) after each test. CI runs the migration check (upgrade, check, downgrade, upgrade) and the tests against a PostgreSQL 17 service.
- **Migrations 0001–0005 are unchanged.** Their `batch_alter_table` blocks run as ordinary `ALTER TABLE` statements on PostgreSQL.
- **No data is carried over** from SQLite. Development databases start again from the sample band, which is fine before the band uses the app for real.

**Alternatives considered:**
- MariaDB. Not taken: it isn't in the stack contract, needs a different driver, only knows named time zones once its time zone tables are loaded, and its `TIMESTAMP` type ends in 2038.
- Keeping SQLite and doing time zone math in Python with `zoneinfo`. It works, and practices already do it, but the instructor wanted the database to handle time zones.
- Running tests on SQLite as well. Not taken: tests that pass on SQLite can fail on PostgreSQL (length limits, text sort order), so the tests should run on the database the app uses.

**Known differences now enforced:** PostgreSQL refuses text longer than its column, where SQLite silently stored it. The request schemas already use the same limits.

---

## 2026-10-28 — Recurring busy times

**Decision:** A member's weekly busy time is stored as a rule, and PostgreSQL works out the real times from it when they're needed. Nothing is stored for each week.
- **Stored:** the member, which days of the week (ISO numbers, 1 is Monday and 7 is Sunday), a start and end clock time, a first date, an optional last date, and the time zone (`America/New_York`, set by the server from `BAND_TIME_ZONE_NAME`). No reason field, as the product owner said.
- **Clock times, not moments.** 8:00 AM stays 8:00 AM all year: PostgreSQL adds the clock time to each date and converts it with `AT TIME ZONE`, which applies daylight saving for that date. Each rule keeps its zone, so a band in another zone later wouldn't change what existing rules mean.
- **Past midnight:** an end time at or before the start time ends the next day (Saturday 10:00 PM to 2:00 AM Sunday). The same start and end time is refused (`422`). The first and last dates limit when a busy time can start.
- **Where they count:** everywhere a one-off busy time counts, from one query (`RecurringBusyTimeRepository.occurrences`): the invite list's busy marks (`weekly_busy_time` conflicts), Find a time, and the calendar.
- **Endpoints:** `/recurring-busy-times` (list, add, change, delete), with the same visibility as one-off busy times: members see and change only their own; the manager and band leader see everyone's. `PATCH` sends every field again. The list has no `q`, because there's no text to search.
- **Calendar:** `GET /busy-times/periods?ends_after=…&starts_before=…` returns one-off busy times and each day of the weekly ones in one list. It isn't paged: the range is limited to 62 days instead (a month view is at most 42), so the calendar never misses entries past a page boundary.
- **Delete is a real delete,** like one-off busy times. A busy time that's no longer true has nothing worth keeping, and the member can always add it again.
- **In the app:** the Add busy time pop-up asks One-off or Repeats weekly. Your busy times lists weekly ones under "Every week" and one-offs under "One-off"; Everyone's busy times lists both under each member.

**Alternatives considered:**
- Storing a row for every week. Not taken: rules with no last date would need rows forever and a job to keep adding them, and the course rule is to compute derived values, not store them.
- Working out the weeks in Python with `zoneinfo`, as Find a time already does for its candidate times. Not taken: the instructor asked for the database to handle time zones, and one query serves the gig page, the calendar and Find a time alike.
- Storing the times in UTC. Not taken: a busy time from 8:00 AM to 5:00 PM would move by an hour every time the clocks change.
- Letting the calendar page through `/busy-times`. Not taken: weekly busy times aren't rows to page through, and a calendar wants everything in its range at once.
- A newer weekly busy time ending an older one automatically. Not taken: the product owner didn't ask for it, and members can have more than one regular commitment (a job and a class).
