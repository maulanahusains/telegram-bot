import { apiRequest } from "./client";

export interface LaunchingBot {
  name: string;
  module_name: string;
}

export interface CurrentUser {
  first_name: string;
  last_name: string | null;
  username: string | null;
  language_code: string | null;
  launching_bot: LaunchingBot;
  session_expires_at: string;
}

interface SessionBootstrap {
  authenticated: true;
  expires_at: string;
}

interface TelegramAuthResponse {
  user: CurrentUser;
  session: SessionBootstrap;
}

export interface TelegramAuthInput {
  launchingBotName: string;
  initData: string;
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/me");
}

export async function authenticateTelegram(
  input: TelegramAuthInput
): Promise<TelegramAuthResponse> {
  return apiRequest<TelegramAuthResponse>("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({
      launching_bot_name: input.launchingBotName,
      init_data: input.initData
    })
  });
}

export async function logout(): Promise<void> {
  await apiRequest<{ ok: true; status: string }>("/auth/logout", {
    method: "POST"
  });
}
