# Changelog

Notable changes to Roadhouse, newest first.

## Unreleased

### Changed
- The database is now PostgreSQL everywhere (Docker Compose, Codespaces, tests and CI). Docker needs a `.env` file with `POSTGRES_PASSWORD`; existing codespaces need rebuilding once.

### Added
- Find a time: when scheduling a practice, the app suggests the best time on each day one to three weeks ahead, never over a gig, and names who can't come.
- Calendar on the Scheduling tab: month and week views of gigs, practices and busy times, with each player in their own color plus initials, a day-by-day list, and arrow-key navigation.
- Practices: the manager and band leader schedule one-time practices and invite any group of players. A practice can't overlap a gig, and one on a gig day needs confirming. Members accept or decline.
- Scheduling: members add, change and delete one-off busy times in a pop-up. The manager and band leader see everyone's. The invite list marks busy players and says why, and lists players who play the role as a secondary instrument.
- Profile tab: everyone sees and edits their own name, phone, email and instruments. Roles are shown but fixed. Phone and email are visible only to that member, the manager and the band leader.
- Band leader: their own place in the user picker. They see every gig with its total pay, everyone's pay and venue contacts, and can change a member's pay.
- Venue contacts are visible only to the manager and band leader.
- The band leader can add, edit and book gigs and invite members, like the manager.
- GitHub Codespaces setup: run the whole app in the browser with `bash scripts/dev.sh`, no Docker needed.
- User picker: continue as the manager or as a band member (sprint 1 stand-in for login).
- Gigs: list, detail, add a potential gig, edit it, and book it.
- Per-gig roles. The manager invites members to each role with their pay, and members accept or decline.
- Members can't accept two gigs that overlap (soundcheck to end).
- Booking needs every invited member, including the band leader, to have accepted.
- Any number of contacts per gig, with notes.
- Load-in, soundcheck and end times computed from the first set time.
- Members list endpoint.
- Made-up sample band, loaded on first start under Docker Compose.

## 2026-10-13

### Added
- App shell: six navigation sections, Docker Compose setup, CI for both apps.

## 2026-10-12

### Added
- Backend foundation: layered FastAPI app, error envelope, health check, CI.
