# Telegram Bot Workspace

This repository is a workspace for a FastAPI/Telegram backend, a responsive
Telegram Mini App/web frontend foundation, and durable Life-product handoff
documentation. The backend remains a modular monolith.

```text
.
├── backend/             # FastAPI, Telegram bot modules, Alembic, Python/uv tooling
├── frontend/            # React + TypeScript + Vite Mini App/web SPA
├── life-docs/           # Permanent Life architecture, decisions, and agent handoff
├── docker-compose.yml   # Workspace orchestration: PostgreSQL, backend, frontend, tunnel
├── .env                 # Untracked, authoritative local stack environment
└── .env.example         # Safe template for the root .env
```

## Working locations

- Run backend-local Python, Alembic, and Make commands from `backend/`. The
  backend Makefile explicitly loads the authoritative root `.env` for commands
  requiring application settings.
- Run workspace Compose commands from this repository root, for example
  `docker compose --profile dev up`.
- Run frontend-local npm commands from `frontend/`, for example `npm ci` and
  `npm run dev`. Its Vite development proxy forwards relative `/api` requests to
  `http://localhost:8000` by default; Docker development forwards them to
  `app-dev` internally.
- `frontend` in the production Compose profile serves the SPA and proxies
  `/api`, `/webhook`, `/health`, and `/admin` to the backend. This is the MVP
  same-origin topology for the HttpOnly platform session cookie.
- `life-docs/` is permanent at repository root. Read its `README.md`, `STATE.md`,
  `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md` before any Life implementation.

For backend architecture, configuration, bot provisioning, and developer
commands, see [backend/README.md](backend/README.md). For frontend setup and
Docker usage, see [frontend/README.md](frontend/README.md).
