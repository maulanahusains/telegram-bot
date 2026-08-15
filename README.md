# Telegram Bot Workspace

This repository is a workspace for a FastAPI/Telegram backend and the planned
Life product documentation. The backend remains a modular monolith; no frontend
application exists yet.

```text
.
├── backend/             # FastAPI, Telegram bot modules, Alembic, Python/uv tooling
├── life-docs/           # Permanent Life architecture, decisions, and agent handoff
├── docker-compose.yml   # Workspace orchestration: PostgreSQL, backend, dev tunnel
├── .env                 # Untracked, authoritative local stack environment
└── .env.example         # Safe template for the root .env
```

## Working locations

- Run backend-local Python, Alembic, and Make commands from `backend/`. The
  backend Makefile explicitly loads the authoritative root `.env` for commands
  requiring application settings.
- Run workspace Compose commands from this repository root, for example
  `docker compose --profile dev up`.
- `life-docs/` is permanent at repository root. Read its `README.md`, `STATE.md`,
  `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md` before any Life implementation.
- `frontend/` is reserved for a future responsive Telegram Mini App/web frontend;
  it is intentionally not present yet.

For backend architecture, configuration, bot provisioning, and developer
commands, see [backend/README.md](backend/README.md).
