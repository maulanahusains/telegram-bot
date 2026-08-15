import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppRoute, LaunchRoute, RootRoute } from "./app/router/AppRouter";

const router = createBrowserRouter([
  { path: "/", element: <RootRoute /> },
  { path: "/app", element: <AppRoute /> },
  { path: "/tg/:launchingBot", element: <LaunchRoute /> },
  { path: "*", element: <RootRoute /> }
]);

export function App() {
  return <RouterProvider router={router} />;
}
