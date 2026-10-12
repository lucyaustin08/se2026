import type { RouteObject } from "react-router";

import { AppLayout } from "./components/AppLayout";
import { NAV_ITEMS } from "./navigation";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SectionPage } from "./pages/SectionPage";

const sectionRoutes: RouteObject[] = NAV_ITEMS.map((item) => {
  const element = <SectionPage title={item.label} description={item.description} />;
  return item.path === "/" ? { index: true, element } : { path: item.path.slice(1), element };
});

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppLayout />,
    children: [...sectionRoutes, { path: "*", element: <NotFoundPage /> }],
  },
];
