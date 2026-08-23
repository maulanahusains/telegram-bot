import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || "http://localhost:8000";
  const configuredHosts = (env.VITE_ALLOWED_HOSTS || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  try {
    if (env.PUBLIC_BASE_URL) {
      configuredHosts.push(new URL(env.PUBLIC_BASE_URL).hostname);
    }
  } catch {
    // Backend settings remain the authoritative validator for PUBLIC_BASE_URL.
  }

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      allowedHosts: [
        "local-bots.maulanah.my.id",
        ...new Set(configuredHosts),
      ],
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true
        },
        "/webhook": {
          target: apiProxyTarget,
          changeOrigin: true
        },
        "/health": {
          target: apiProxyTarget,
          changeOrigin: true
        }
      }
    }
  };
});
