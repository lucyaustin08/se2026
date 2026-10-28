# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **The band manager** (one per band, also usually the band leader). Books gigs, chooses each gig's instrumentation, invites members to roles with their pay, builds setlists and keeps everyone organized. Works mostly **on a laptop**, at a desk, often with several gigs in progress at once.
- **Band members.** Need to know where to be, when, what to play and in what key, and to say when they can and can't play. Use it mostly **on a phone**, often on the move or at the venue: checking load-in time, the address, or the setlist.

Roadhouse is built for a **real band** run by the product owner, who plans to use it for actual paid gigs. Requirements come from the product owner through the team.

## Product Purpose

Put a band's gigs, songs, setlists and people in one place, replacing scattered texts, calendars and spreadsheets. Success means the manager can take a gig from first lead to booked without leaving the app, and every member always knows where they're playing next and what they're playing.

## Positioning

Built around how a working band actually runs a gig, not generic scheduling:
- A gig starts as a **pending lead** with whatever is known, and can only be **booked** once it's complete. The app says exactly what's still missing.
- Load-in, soundcheck and end times follow the first set time automatically.
- Lineups are **personal**: the manager invites specific people to specific roles and asks a backup when someone can't make it. Nothing is auto-assigned.
- Members see only what's theirs. Other booked dates show as "Not assigned", so they know the band is busy without seeing details or pay.

## Operating Context

- Gig lifecycle: pending → booked, or cancelled (kept and shown as cancelled).
- Gig day: load-in (default 2h before first set), soundcheck (default 1h before), first set, end. Gigs usually run two to three hours; members stay the whole show and may request to arrive late, never to leave early.
- Lineups: solo, duo, trio, quartet or full band; a gig can't go ahead without the band leader. A member can't accept two overlapping gigs.
- Contacts vary per gig: any number, with names, phones, emails and notes.
- Invites are sent as a copied link through whatever channel the manager already uses.
- App sections: Dashboard, Gigs, Scheduling, Songs & Setlists, Members, Booking.

## Capabilities and Constraints

- Built so far: gig list (with an "Undated" group for drafts), gig detail, add/edit a pending gig, booking, per-gig roles with invitations, accept/decline, contacts, computed times.
- Not built yet: songs and setlists, scheduling/availability, members management, booking pipeline, dashboard, real login (a user picker stands in during sprint 1).
- All times are entered and shown in the browser's local time zone; out-of-town time zones are not supported.
- Members never see pay or pending gigs.
- Technical stack, conventions and accessibility floor are fixed by `CLAUDE.md`; product decisions are recorded in `DECISIONS.md`.
- **Open:** whether every lineup slot must be filled before booking; how late-arrival requests are resolved; how each member's pay share is shown to them.

## Brand Commitments

- Name: **Roadhouse**.
- Voice: plain and direct, with gig-world words (load-in, soundcheck, setlist, set) used naturally and a little warmth. No jokes in errors.
- The team chose the "Gig Poster" visual direction on 2026-10-21; its tokens and fonts live in `frontend/src/styles/index.css` (see `DECISIONS.md`).
- Status must never be shown by color alone.

## Evidence on Hand

- The only data is a made-up sample band seeded for development (`backend/app/seed.py`). Its names are not real people.
- The real band's name, members, venues and photos are not in the repo. Do not invent them, or any testimonials, gig counts or quotes.

## Product Principles

1. **The gig is the unit of work.** Every screen should help someone get a specific gig right.
2. **Show what's missing, don't just refuse.** When the app blocks an action, it says what to do next.
3. **Each person sees their own job.** The manager gets the whole picture; members get exactly what they need, on a phone, fast.
4. **Personal, not automated.** The app supports the manager's choices about who plays; it doesn't make them.
5. **One rule, one place.** Derived times and booking readiness come from the server, so screens and rules never disagree.

## Accessibility & Inclusion

The course accessibility floor applies (labels on every control, errors tied with `aria-describedby`, nothing by color alone, full keyboard use). Members' screens must work comfortably on a phone, in poor light at a venue, with large enough tap targets.
