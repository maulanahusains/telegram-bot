# Telegram Platform Frontend

This is the single responsive React Mini App/web frontend. It is Life-first but
is deliberately launchable by any configured Telegram bot; product screens are
added only in their authorized phases.

## Local development

Install dependencies from this directory, then start Vite:

```bash
npm ci
npm run dev
```

The browser calls relative `/api/v1/*` paths. Vite proxies `/api` to
`http://localhost:8000` by default. Set the public, non-secret
`VITE_API_PROXY_TARGET` environment variable only when the backend is elsewhere.

For local HTTP development, set
`APPLICATION_SESSION_COOKIE_SECURE=false` in the untracked root `.env`; keep the
production default `true`. Do not put bot credentials, Telegram `initData`, or
session values in frontend environment files.

## Docker

From the workspace root:

```bash
docker compose --profile dev up frontend-dev
docker compose --profile prod up frontend
```

`frontend-dev` runs Vite at `http://localhost:${FRONTEND_DEV_PORT:-5173}` and
proxies API calls internally to `app-dev`. `frontend` is the production Nginx
image at `http://localhost:${FRONTEND_PORT:-8080}`. It serves the SPA and proxies
`/api`, `/webhook`, `/health`, and `/admin` to the production backend service,
so the externally used frontend origin can remain the same origin for the API
session cookie.

No frontend service is responsible for Telegram signature validation. The only
trusted auth exchange is `POST /api/v1/auth/telegram` to the backend.
