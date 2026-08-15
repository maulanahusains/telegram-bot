import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

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
          <p className="eyebrow">Authenticated session</p>
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

      <section className="app-card">
        <h2>Application shell is ready</h2>
        <dl>
          <div>
            <dt>Launching bot</dt>
            <dd>{user.launching_bot.name}</dd>
          </div>
          <div>
            <dt>Module</dt>
            <dd>{user.launching_bot.module_name}</dd>
          </div>
          <div>
            <dt>Session expires</dt>
            <dd>{new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(user.session_expires_at))}</dd>
          </div>
        </dl>
        <p>
          Life screens are intentionally not available yet. This shell validates the shared frontend, Mini App, and platform-authentication boundary.
        </p>
      </section>
    </main>
  );
}
