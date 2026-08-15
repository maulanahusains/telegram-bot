export type TelegramThemeParams = Record<string, string | undefined>;

interface TelegramWebApp {
  initData: string;
  version?: string;
  platform?: string;
  colorScheme?: "light" | "dark";
  themeParams?: TelegramThemeParams;
  ready(): void;
  expand(): void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

export interface TelegramLaunchContext {
  isTelegram: boolean;
  initData: string | null;
  platform: string | null;
  version: string | null;
  colorScheme: "light" | "dark" | null;
}

export function initializeTelegramWebApp(): TelegramLaunchContext {
  const webApp = window.Telegram?.WebApp;
  if (!webApp) {
    return {
      isTelegram: false,
      initData: null,
      platform: null,
      version: null,
      colorScheme: null
    };
  }

  webApp.ready();
  webApp.expand();
  applyTelegramTheme(webApp.themeParams);

  return {
    isTelegram: true,
    initData: webApp.initData || null,
    platform: webApp.platform ?? null,
    version: webApp.version ?? null,
    colorScheme: webApp.colorScheme ?? null
  };
}

function applyTelegramTheme(theme: TelegramThemeParams | undefined): void {
  if (!theme) {
    return;
  }
  const root = document.documentElement;
  setThemeValue(root, "--tg-bg", theme.bg_color);
  setThemeValue(root, "--tg-surface", theme.secondary_bg_color);
  setThemeValue(root, "--tg-text", theme.text_color);
  setThemeValue(root, "--tg-muted", theme.hint_color);
  setThemeValue(root, "--tg-link", theme.link_color);
  setThemeValue(root, "--tg-button", theme.button_color);
  setThemeValue(root, "--tg-button-text", theme.button_text_color);
}

function setThemeValue(root: HTMLElement, property: string, value: string | undefined): void {
  if (value) {
    root.style.setProperty(property, value);
  }
}
