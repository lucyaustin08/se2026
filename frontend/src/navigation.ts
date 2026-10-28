/** The app's main sections, in the order they appear in the navigation. */
export interface NavItem {
  path: string;
  label: string;
  description: string;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    path: "/",
    label: "Dashboard",
    description: "Upcoming gigs and practices, and what needs attention.",
  },
  { path: "/gigs", label: "Gigs", description: "Every gig, with its venue, pay and schedule." },
  {
    path: "/scheduling",
    label: "Scheduling",
    description: "Availability and practice times.",
  },
  {
    path: "/songs",
    label: "Songs & Setlists",
    description: "The band's repertoire and setlists.",
  },
  { path: "/members", label: "Members", description: "Who's in the band and what they play." },
  { path: "/booking", label: "Booking", description: "Venues and potential gigs." },
  { path: "/profile", label: "Profile", description: "Your details and instruments." },
];
