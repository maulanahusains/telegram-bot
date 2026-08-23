import { useMutation, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { logout, type CurrentUser } from "../../app/api/auth";
import { BottomNav, IconButton } from "./LifeUI";
import { Icon } from "./icons";

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
  const initials = [user.first_name, user.last_name].filter(Boolean).map((part) => part[0]).join("").slice(0, 2).toUpperCase();

  return (
    <main className="app-page">
      <header className="life-topbar">
        <NavLink className="life-brand" to="/app/today" end aria-label="Life home"><span className="brand-mark"><Icon name="leaf" size={20} /></span><span>Life</span></NavLink>
        <div className="topbar-actions">
          <IconButton label="View notifications" icon="bell" />
          <button className="avatar" type="button" onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending} aria-label={logoutMutation.isPending ? "Signing out" : "Log out"} title={logoutMutation.isPending ? "Signing out" : "Log out"}>{initials || "L"}</button>
        </div>
      </header>
      <Outlet />
      <BottomNav />
    </main>
  );
}
