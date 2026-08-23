import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { AppRoute, LaunchRoute, RootRoute } from "./app/router/AppRouter";
import { GroceryPage, PlannerPage, ProgressPage, SettingsPage, TodayPage } from "./app/router/AppRouter";

const router = createBrowserRouter([
  { path: "/", element: <RootRoute /> },
  { path: "/app", element: <AppRoute />, children: [
    { index: true, element: <Navigate to="today" replace /> },
    { path: "today", element: <TodayPage /> },
    { path: "planner", element: <PlannerPage /> },
    { path: "grocery", element: <GroceryPage /> },
    { path: "progress", element: <ProgressPage /> },
    { path: "settings", element: <SettingsPage /> }
  ] },
  { path: "/tg/:launchingBot", element: <LaunchRoute /> },
  { path: "*", element: <RootRoute /> }
]);

export function App() {
  return <RouterProvider router={router} />;
}
