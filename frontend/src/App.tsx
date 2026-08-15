import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { AppRoute, LaunchRoute, RootRoute } from "./app/router/AppRouter";
import { PlannerPage, SettingsPage } from "./app/router/AppRouter";

const router = createBrowserRouter([
  { path: "/", element: <RootRoute /> },
  { path: "/app", element: <AppRoute />, children: [
    { index: true, element: <Navigate to="planner" replace /> },
    { path: "planner", element: <PlannerPage /> },
    { path: "settings", element: <SettingsPage /> }
  ] },
  { path: "/tg/:launchingBot", element: <LaunchRoute /> },
  { path: "*", element: <RootRoute /> }
]);

export function App() {
  return <RouterProvider router={router} />;
}
