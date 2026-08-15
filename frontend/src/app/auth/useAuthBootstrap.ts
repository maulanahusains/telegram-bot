import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authenticateTelegram, getCurrentUser, type CurrentUser } from "../api/auth";
import { ApiError } from "../api/client";
import {
  initializeTelegramWebApp,
  type TelegramLaunchContext
} from "../telegram/webapp";

const currentUserQueryKey = ["platform", "current-user"] as const;
const BOT_NAME_PATTERN = /^[a-z][a-z0-9_]{0,63}$/;

export type AuthBootstrapState =
  | { kind: "loading" }
  | { kind: "authenticated"; user: CurrentUser; telegram: TelegramLaunchContext }
  | { kind: "outside_telegram" }
  | { kind: "missing_launch_context" }
  | { kind: "invalid_launch_context" }
  | { kind: "authentication_failed"; message: string }
  | { kind: "service_error"; message: string };

export function useAuthBootstrap(launchingBotName?: string): AuthBootstrapState {
  const queryClient = useQueryClient();
  const telegram = useMemo(() => initializeTelegramWebApp(), []);
  const [loginAttempted, setLoginAttempted] = useState(false);
  const currentUser = useQuery({
    queryKey: currentUserQueryKey,
    queryFn: getCurrentUser
  });
  const login = useMutation({
    mutationFn: authenticateTelegram,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: currentUserQueryKey });
    }
  });

  const botNameIsValid = launchingBotName
    ? BOT_NAME_PATTERN.test(launchingBotName)
    : false;
  const currentUserError = currentUser.error;
  const isUnauthenticated =
    currentUserError instanceof ApiError && currentUserError.status === 401;

  useEffect(() => {
    if (
      !isUnauthenticated ||
      loginAttempted ||
      login.isPending ||
      !telegram.isTelegram ||
      !telegram.initData ||
      !launchingBotName ||
      !botNameIsValid
    ) {
      return;
    }

    setLoginAttempted(true);
    login.mutate({ launchingBotName, initData: telegram.initData });
  }, [
    botNameIsValid,
    isUnauthenticated,
    launchingBotName,
    login,
    loginAttempted,
    telegram.initData,
    telegram.isTelegram
  ]);

  if (currentUser.isPending || login.isPending) {
    return { kind: "loading" };
  }
  if (currentUser.data) {
    return { kind: "authenticated", user: currentUser.data, telegram };
  }
  if (!isUnauthenticated) {
    return { kind: "service_error", message: publicErrorMessage(currentUserError) };
  }
  if (!telegram.isTelegram) {
    return { kind: "outside_telegram" };
  }
  if (!launchingBotName) {
    return { kind: "missing_launch_context" };
  }
  if (!botNameIsValid) {
    return { kind: "invalid_launch_context" };
  }
  if (!telegram.initData) {
    return { kind: "authentication_failed", message: "Telegram did not provide launch data. Close this page and open the Mini App again from its bot." };
  }
  if (login.error) {
    return { kind: "authentication_failed", message: publicErrorMessage(login.error) };
  }
  return { kind: "loading" };
}

function publicErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "The service could not be reached. Please try again shortly.";
}
