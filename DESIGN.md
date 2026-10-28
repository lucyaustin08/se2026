---
name: Roadhouse
description: A band's gigs, songs, setlists and people in one place, styled like a gig poster.
colors:
  paper: "#f4ecdd"
  ink: "#1e1a17"
  ink-faded: "#5e554c"
  poster-red: "#b8321e"
  poster-red-deep: "#8e2414"
  poster-red-tint: "#f6ded6"
  mustard: "#e2a72e"
  navy: "#22355e"
  paper-shade: "#ebe1cf"
  rule-light: "#ddd2bf"
  rule: "#c9bca6"
  rule-strong: "#a8998a"
  ink-muted: "#4a423b"
typography:
  headline:
    fontFamily: "Anton, Arial Narrow, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 400
    lineHeight: 1.33
  title:
    fontFamily: "Anton, Arial Narrow, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  body-strong:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
  label:
    fontFamily: "Archivo, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.43
rounded:
  none: "0px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.poster-red-deep}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.poster-red}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.paper-shade}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
  gig-row:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
  gig-row-hover:
    backgroundColor: "{colors.poster-red-tint}"
  gig-row-restricted:
    backgroundColor: "{colors.paper-shade}"
    textColor: "{colors.ink-faded}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
  nav-tab-active:
    backgroundColor: "{colors.poster-red-tint}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "8px 12px"
---

# Design System: Roadhouse

> **Migration status (2026-10-27):** the tokens below are live in `frontend/src/styles/index.css`, but the shared layout and components have not been restyled yet. They still render on white, with 4px rounded corners and Archivo headings. This file describes the **committed target** the team chose (see `DECISIONS.md`, 2026-10-21). Build new screens to this file. Bring old ones over when the restyle happens. Don't copy the current white and rounded classes into new code.

## Overview

**Creative North Star: "The Gig Poster"**

Roadhouse looks like the poster pinned up outside the venue: heavy condensed headlines in ink on warm paper, with a few loud printed colors. It's a working tool, though, not a poster. The identity is in the headings, the status marks and the square, printed edges. Everything people actually work with (gig rows, forms, times, addresses) stays calm and plain, and is easy to read on a phone in a dim room.

The density is moderate. The manager scans lists of gigs on a laptop, and members check a single gig on a phone. Color is spent on meaning (status, the main action, an invitation waiting for an answer), never on decoration.

**Key Characteristics:**
- Warm paper background, near-black ink text, no pure white or pure gray.
- Anton for page and section headings only. Archivo for everything else.
- Square corners everywhere. Edges are drawn with flat borders, not shadows.
- Poster red is reserved for the main action and active states. Mustard and navy are spot colors.
- Every status is shown by a word plus a line style, never by color alone.

## Colors

A printed three-ink palette (red, mustard, navy) on warm paper, with a family of warm grays for borders and secondary text.

### Primary
- **Poster Red** (`poster-red`): booked status, hover on the main button, and focus outlines. It passes contrast as text on paper, but keep it for marks and fills, not paragraphs. Its Tailwind alias is `brand-600`.
- **Deep Poster Red** (`poster-red-deep`): the main button's fill, links and back-links. It also passes contrast as body-size text on paper. Its Tailwind alias is `brand-700`.
- **Red Tint** (`poster-red-tint`): the active navigation tab, hover on gig rows, and the "Invited: please answer" badge. It's a background only. Its Tailwind alias is `brand-50`.

### Secondary
- **Mustard** (`mustard`): the pending-gig status mark. **It fails contrast as text on paper.** Use it only as a fill or border, with ink text on top.

### Tertiary
- **Navy** (`navy`): the edge of a practice on the calendar (a solid 4px left border), the way poster red marks a gig. It passes contrast as text on paper and as a fill under paper-colored text. Don't spread it beyond practices without a reason.

### Member colors (calendar only)
- **`member-1` to `member-8`** (sage, sky, clay, lilac, wheat, rose, sea glass, stone): soft fills that tell members' busy times apart on the calendar. **They are an exception to the Three Inks Rule, for the calendar only.** Text on them is always ink, they always carry the member's initials or name, and busy times also have a dashed ink edge, so nothing depends on color alone. Players get colors in the order they joined, and the manager, who doesn't play, has none. Don't use them anywhere else.

### Neutral
- **Paper** (`paper`): the page background, and the fill of rows, inputs and secondary buttons.
- **Ink** (`ink`): all primary text. Its Tailwind alias is `ink-900`.
- **Faded Ink** (`ink-faded`): secondary text such as dates, "Not set" and helper lines, plus the cancelled status. Its Tailwind alias is `gray-600`.
- **Muted Ink** (`ink-muted`): body-size secondary text that needs a bit more weight. Its Tailwind alias is `gray-700`.
- **Paper Shade** (`paper-shade`): restricted "Not assigned" rows, and hover on secondary buttons. Its Tailwind alias is `gray-100`.
- **Rules** (`rule-light`, `rule`, `rule-strong`): borders from light to strong. Use them for dividers, row edges and input edges. **They are not for text.** `rule-strong` is borderline at 3.5:1. Its Tailwind aliases are `gray-200`, `gray-300` and `gray-400`.

### Named Rules
**The Three Inks Rule.** Red, mustard and navy are the only hues, apart from the calendar's member colors. Don't add a fourth accent, and don't use Tailwind's default palette (`red-*`, `blue-*`, `green-*`). The error box still uses Tailwind's default reds and has to move to this palette in the restyle.

**The Paper Not White Rule.** Surfaces are `paper` or `paper-shade`. Never `#fff` and never a cool gray.

**The Mustard Is Never Text Rule.** Mustard sits behind ink, never under paper and never as letters.

## Typography

**Display Font:** Anton (with Arial Narrow, sans-serif)
**Body Font:** Archivo (with ui-sans-serif, system-ui)

**Character:** Anton is the poster headline: tall, condensed, a single weight. Archivo is the sturdy grotesque underneath, which reads well at small sizes on a phone. Both are self-hosted from `frontend/public/fonts` under the SIL Open Font License.

### Hierarchy
- **Headline** (Anton 400, 1.5rem): the page `h1`, such as "Gigs" or a venue name.
- **Title** (Anton 400, 1.125rem): section `h2`s, such as "By date", "Schedule" and "Lineup".
- **Body** (Archivo 400, 1rem, 1.5): all reading text, field values, times and addresses.
- **Body Strong** (Archivo 600, 1rem): the venue name in a gig row, "Not assigned", and the active nav tab.
- **Label** (Archivo 500, 0.875rem): form labels, status words, helper text and the meta line in a gig row.

### Named Rules
**The Headline Only Rule.** Anton is for `h1` and `h2` only. Never use it for buttons, labels, table cells, times or anything a member reads at a glance to act on. Condensed type costs legibility at small sizes.

**The One Weight Rule.** Anton ships one weight (400). Don't apply `font-bold` to it. The browser would fake a bold.

## Layout

A single centered column, at most 64rem wide (`max-w-5xl`), with 16px side gutters. The header holds the wordmark, the section tabs and who is acting. The tabs scroll sideways on narrow screens rather than wrapping. Content sits below in a 24px vertical rhythm. Section headings are 24px apart, and items inside a section are 8px apart.

Spacing follows Tailwind's 4px scale. The steps in real use are 4, 8, 12, 16, 24 and 32px. Detail pages use a two-column term/value grid from the `sm` breakpoint (640px) up, and stack on phones. Forms are one column on phones and two or three columns from `sm` up.

**The Thumb Rule.** Anything a member taps on a phone, such as gig rows, Accept and Decline, is at least 44px tall.

## Elevation & Depth

The system is flat. There are no shadows anywhere, and none should be added. Depth comes from print logic: a border marks an edge, `paper-shade` marks a quieter surface, and `poster-red-tint` marks a highlighted one. An invitation that needs an answer is shown with a red border and red-tint fill, not by lifting the card off the page.

**The Printed Flat Rule.** If you want a shadow, use a border or a tint instead.

## Shapes

Every corner is square (0px): buttons, inputs, rows, badges, tabs and alerts. That's the committed target. The current code still uses `rounded` (4px) and has to drop it in the restyle. Borders are 1px solid by default. Line style carries meaning in status marks (see Components), so don't use dashed or struck-through styles for decoration.

## Components

### Buttons
- **Shape:** square corners (0px).
- **Primary:** a Deep Poster Red fill with paper text, Archivo 500 at 1rem, padding 8px 16px. Use one per view, for the main action ("Add gig", "Book gig", "Accept").
- **Hover / Focus:** hover changes the fill to Poster Red. Focus shows a 2px Poster Red outline, offset 2px.
- **Secondary:** a paper fill, ink text and a 1px `rule-strong` border, with a Paper Shade hover. Use it for "Decline", "Switch user", "Add contact" and "Try again". A disabled button drops to 60% opacity.

### Status Marks (signature)
Every gig status is a word plus a line style plus a color, so it still reads in grayscale:
- **Pending:** a dashed Mustard border, with the word "Pending" in ink.
- **Booked:** a solid Poster Red border, with the word "Booked" in ink.
- **Cancelled:** a solid Faded Ink border, with the word "Cancelled" struck through in Faded Ink.

Use the `status-potential`, `status-booked` and `status-cancelled` tokens in `index.css`. The token name still says "potential" while the label says "Pending".

### Gig Rows / Containers
- **Corner Style:** square.
- **Background:** paper. Hover changes it to Red Tint.
- **Border:** 1px `rule`.
- **Internal Padding:** 12px 16px.
- **Content:** the venue name in Body Strong, then the date and time in Label in Muted Ink, then a meta line with the lineup, the status mark and the invitation badge.
- **Restricted ("Not assigned"):** a Paper Shade fill, Faded Ink text and a `rule-light` border, with "Not assigned" in Body Strong above the date. It isn't a link and has no hover. The text carries the meaning, not the gray.

### Inputs / Fields
- **Style:** a paper fill, a 1px `rule-strong` border, square corners, padding 8px 12px and full width. The label sits above in Archivo 500.
- **Focus:** a 2px Poster Red outline.
- **Error:** the border changes to a deep red, and the message is linked with `aria-describedby`. The error red still has to be mapped to the palette (see the Three Inks Rule).

### Alerts
The error box with "Try again" is still in Tailwind's default reds with rounded corners. During the restyle it moves to square corners and the poster red family, and keeps `role="alert"` and the retry button.

### Navigation
The tabs are Archivo at 0.875rem with padding 8px 12px, laid out in one horizontal row that scrolls sideways on phones. The active tab has a Red Tint fill, weight 600 and an underline, so it never relies on color alone. Inactive tabs get a Paper Shade fill on hover. The wordmark "Roadhouse" sits above the tabs.

## Do's and Don'ts

### Do:
- **Do** use the named tokens (`paper`, `ink`, `poster-red`, `mustard`, `navy`, `status-*`) in new code, and `font-display` for `h1` and `h2`.
- **Do** pair every status color with its word and its line style (dashed, solid, struck through).
- **Do** keep times, addresses and lineup in Archivo at 1rem or larger on member-facing screens.
- **Do** show focus with a 2px Poster Red outline on every interactive element.

### Don't:
- **Don't** use rounded corners, shadows or a white background in new work.
- **Don't** use Anton for buttons, labels, body text or anything below a section heading.
- **Don't** put text in Mustard or the rule grays.
- **Don't** reach for Tailwind's default color palette. Its colors aren't part of the system.
- **Don't** add poster decoration (torn edges, halftone textures, distressed type) to rows, forms or tables. The poster lives in the headings and the status marks.
