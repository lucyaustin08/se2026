# Changelog

Notable changes to Roadhouse, newest first.

## Unreleased

### Added
- User picker: continue as the manager or as a band member (sprint 1 stand-in for login).
- Gigs: list, detail, add a potential gig, edit it, and book it.
- Per-gig roles. The manager invites members to each role with their pay, and members accept or decline.
- Members can't accept two gigs that overlap (load-in to end).
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
