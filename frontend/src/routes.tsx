import type { RouteObject } from "react-router";

import { AppLayout } from "./components/AppLayout";
import { NAV_ITEMS } from "./navigation";
import { EditGigPage } from "./pages/EditGigPage";
import { GigDetailPage } from "./pages/GigDetailPage";
import { GigsPage } from "./pages/GigsPage";
import { LoginPage } from "./pages/LoginPage";
import { NewGigPage } from "./pages/NewGigPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SectionPage } from "./pages/SectionPage";

const BUILT_SECTIONS = new Set(["/gigs"]);

// Sections whose feature isn't built yet get a placeholder page.
const placeholderRoutes: RouteObject[] = NAV_ITEMS.filter(
  (item) => !BUILT_SECTIONS.has(item.path),
).map((item) => {
  const element = <SectionPage title={item.label} description={item.description} />;
  return item.path === "/" ? { index: true, element } : { path: item.path.slice(1), element };
});

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      ...placeholderRoutes,
      { path: "gigs", element: <GigsPage /> },
      { path: "gigs/new", element: <NewGigPage /> },
      { path: "gigs/:gigId", element: <GigDetailPage /> },
      { path: "gigs/:gigId/edit", element: <EditGigPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
