import { Navigate, useParams } from "react-router-dom";

import { useAuthBootstrap } from "../auth/useAuthBootstrap";
import { AppState } from "../../shared/components/AppState";
import { LifeShell } from "../../modules/life/LifeShell";

export function LaunchRoute() {
  const { launchingBot } = useParams<{ launchingBot: string }>();
  return <BootstrapPage launchingBot={launchingBot} returnPath={launchingBot ? `/tg/${launchingBot}` : "/app"} />;
}

export function AppRoute() {
  return <BootstrapPage returnPath="/app" />;
}

export function RootRoute() {
  return <Navigate to="/app" replace />;
}

function BootstrapPage({ launchingBot, returnPath }: { launchingBot?: string; returnPath: string }) {
  const state = useAuthBootstrap(launchingBot);

  switch (state.kind) {
    case "loading":
      return <AppState title="Connecting to Telegram">Checking your secure application session…</AppState>;
    case "authenticated":
      return <LifeShell user={state.user} returnPath={returnPath} />;
    case "outside_telegram":
      return <AppState title="Open this app from Telegram">Sign-in for this MVP uses Telegram Mini App verification. Open the application from a configured Telegram bot to continue.</AppState>;
    case "missing_launch_context":
      return <AppState title="Open this app from its bot">A Telegram session is available, but this link does not identify the bot that launched the Mini App.</AppState>;
    case "invalid_launch_context":
      return <AppState title="Invalid launch link">This link has an invalid bot reference. Reopen the Mini App from Telegram.</AppState>;
    case "authentication_failed":
      return <AppState title="Telegram sign-in was not accepted">{state.message}</AppState>;
    case "service_error":
      return <AppState title="Service temporarily unavailable">{state.message}</AppState>;
  }
}
