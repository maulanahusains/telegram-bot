import { useMutation, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { logout, type CurrentUser } from "../../app/api/auth";

interface LifeShellProps {
  user: CurrentUser;
  returnPath: string;
}

export function LifeShell({ user, returnPath }: LifeShellProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: async () => {
      queryClient.removeQueries({ queryKey: ["platform", "current-user"] });
      await navigate(returnPath, { replace: true });
    }
  });
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ");

  return (
    <main className="app-page">
      <header className="app-header">
        <div>
          <p className="eyebrow">Life</p>
          <h1>Welcome, {displayName}</h1>
        </div>
        <button
          className="button button-secondary"
          type="button"
          onClick={() => logoutMutation.mutate()}
          disabled={logoutMutation.isPending}
        >
          {logoutMutation.isPending ? "Signing out…" : "Log out"}
        </button>
      </header>

      <nav className="app-nav" aria-label="Life navigation"><NavLink to="/app/planner">Planner</NavLink><NavLink to="/app/settings">Settings</NavLink></nav>
      <Outlet />
    </main>
  );
}
