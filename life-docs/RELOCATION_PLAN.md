# Phase 0A — Backend Relocation Plan

## Scope and invariant

**CONFIRMED REQUIREMENT:** before Phase 1, move the existing FastAPI backend into `project-root/backend/`. `life-docs/` remains exactly `project-root/life-docs/`; do not move it into backend. `frontend/` is not created by this phase.

This is a filesystem/configuration relocation only. Do not add Life code, tables, migrations, authentication, scheduler changes, or behavior refactors. Keep it isolated in its own change/commit where possible so Git recognizes file renames and review remains tractable.

## Verified current working-directory assumptions

| Current artifact | Verified assumption | Required post-move change |
| --- | --- | --- |
| `app/` | Python package imported as `app.main:app` from root project context | Move to `backend/app/`; module imports stay `app.*` when commands run from `backend/`/container `/app` |
| `pyproject.toml`, `uv.lock` | `uv` project metadata at root | Move to `backend/`; run `uv` commands from `backend/` |
| `alembic.ini` | `script_location = migrations`, `prepend_sys_path = .` | Move to `backend/`; relative values remain correct from `backend/` |
| `migrations/` | `migrations/env.py` imports `app.*` | Move intact to `backend/migrations/`; imports need no rename if Alembic cwd is backend |
| `Dockerfile` | copies root `pyproject.toml`, lock, README, app, migrations, Alembic | Move to `backend/Dockerfile`; retain its internal relative COPY paths and build with context `./backend` |
| `docker-compose.yml` | root stack owns Postgres/app/app-dev/cloudflared; contexts/mounts target root | Keep root-level; change backend build context, Dockerfile, env file, dev bind mounts, and command assumptions to `./backend/...` |
| `Makefile` | invokes `uv`/Alembic in current directory and Compose from root | Move backend developer Python targets to `backend/Makefile`; provide root Compose targets separately only if needed |
| `README.md` | describes backend and root-relative commands | Move/replace as `backend/README.md`; write/update a root project README that links backend/life-docs and future frontend |
| `.env` loading | `Settings` has `env_file=".env"`; root `.env`, `.env.example`, and `.gitignore` exist; Compose uses an env file | Keep root `.env` as canonical. Compose uses `env_file: ./.env`; `backend/Makefile` exports `../.env` before Uvicorn/Alembic commands. Do not duplicate secrets. |
| `cloudflared` | root Compose’s tunnel depends on `app-dev`; tunnel origin is documented as `http://app-dev:8000` | Keep service/root Compose and origin unchanged; only backend service build/mount paths change |

## Files/directories to move into `backend/`

Move as a unit:

```text
app/
migrations/
Dockerfile
Makefile
README.md                         # backend-specific README; replace root README separately
alembic.ini
pyproject.toml
uv.lock
docker/README.md                  # move `docker/` too if it contains only backend Docker docs
```

Current repository inspection found `docker/README.md` only under `docker/`; it is backend-owned documentation. Move the whole `docker/` directory to `backend/docker/` if no future root-stack assets are placed there.

## Files/directories to remain root-level

```text
life-docs/                        # permanent; never move
docker-compose.yml                # root stack orchestration (PostgreSQL/backend/tunnel; later frontend)
README.md                         # new root workspace overview after backend README is moved
.env                              # recommended root stack/deployment env file, untracked
.gitignore                        # existing root-wide ignore policy; preserved unchanged
frontend/                         # absent now; future sibling
ARCHITECTURE_ANALYSIS.md           # absent at Phase 0A execution; no file was moved or duplicated
```

The root `.env` is untracked and ignored; `.env.example`, `.gitignore`, and `.dockerignore` exist. `.dockerignore` moves to `backend/.dockerignore` because Docker build context becomes `./backend`. No CI workflow, scripts directory, or test directory was found. Preserve existing root ignore rules; do not overwrite the user’s `.env`.

## Exact relocation sequence

1. Read `git status --short` and inventory root files. Inspect `ARCHITECTURE_ANALYSIS.md` Git state before moving it; do not discard an untracked/user-owned copy.
2. Create `backend/` and perform Git-aware moves of the backend-owned files/directories listed above. Keep package name `app`, so internal import statements remain unchanged.
3. Keep root `docker-compose.yml`; update only path references:
   - `build.context: ./backend`
   - `build.dockerfile: Dockerfile` relative to that context (or `./backend/Dockerfile` if Compose syntax is deliberately chosen consistently)
   - backend service `env_file: ./.env` if root `.env` remains canonical
   - development volumes: `./backend/app:/app/app`, `./backend/migrations:/app/migrations`, `./backend/alembic.ini:/app/alembic.ini`
   - preserve `cloudflared → app-dev` network origin `http://app-dev:8000`
   - preserve ports, profiles, Postgres volume, health checks, and app service names unless a separate deployment change is approved.
4. Keep `backend/Dockerfile` container layout as `/app` with copied `app`, `migrations`, Alembic, Python project files; because context is backend, its existing `COPY app`, `COPY migrations`, and relative metadata copies remain valid. Do not change application import target `app.main:app`.
5. Keep `backend/alembic.ini` relative `script_location = migrations` and `prepend_sys_path = .`; it becomes correct when all Alembic commands are launched in `backend/`. Ensure Compose migration command continues running in container `/app`.
6. Move Makefile developer targets to `backend/Makefile`; change only root-stack targets deliberately. Recommended root convention after move: use `docker compose ...` from root; use `make -C backend run|migrate|revision` or `cd backend && make ...` for Python commands. Add a small root Makefile only if the team wants aliases; do not duplicate command logic silently.
7. Resolve `.env` behavior explicitly:
   - The existing untracked root `.env` remains the only authoritative local stack environment because root Compose interpolates `${...}` before service `env_file` processing.
   - Root Compose passes it to backend services through `env_file: ./.env`.
   - `backend/Makefile` uses POSIX-shell `set -a; . ../.env; set +a` before backend-local Uvicorn/Alembic commands. Direct `uv run` callers must source the same root file first or use those Make targets.
   - `Settings.env_file=".env"` remains unchanged; container services receive exported Compose environment, while Make exports root values for local commands. No secrets are copied.
8. Split documentation: root `README.md` becomes workspace overview with backend/life-docs/frontend instructions; `backend/README.md` retains/updates backend architecture, CLI, Makefile, Docker, and command paths. Update `life-docs` references from root `app/...` to future `backend/app/...` only after move, while retaining facts about pre-move paths where historical context matters.
9. Update any remaining references found via `rg` to `./app`, `./migrations`, root `Dockerfile`, `alembic.ini`, `pyproject.toml`, root `README.md`, `uv run`, and root Compose invocation. Current known references are `Dockerfile`, `docker-compose.yml`, `Makefile`, README, `alembic.ini`, `migrations/env.py`, `pyproject.toml`, and life docs.
10. Do not change migration revision contents or generate an Alembic revision. Finish by recording Phase 0A status in `life-docs/STATE.md`.

## Planned verification commands (do not run unless policy/scope authorizes)

The current repository `AGENTS.md` prohibits this agent from running tests, linters, formatters, type checks, builds, or automated runtime validation. These commands are planned for a developer/authorized relocation task:

```bash
git status --short
git diff --check
rg -n "(^|[ ./])app/|\./migrations|Dockerfile|alembic\.ini|pyproject\.toml|uv run" . -g '!graphify-out/**'
cd backend && uv run python -c "import app.main; print(app.main.app.title)"
cd backend && uv run alembic current
cd backend && uv run alembic heads
docker compose config
docker compose --profile dev build app-dev
docker compose --profile dev up -d postgres app-dev cloudflared
docker compose --profile dev ps
curl --fail http://localhost:${APP_PORT:-8000}/health
docker compose --profile dev down
```

If an existing test suite is added by the time relocation occurs, run its documented backend command from `backend/`. Planning inspection found no committed test files. Production migration upgrade/start commands should be executed only in an approved environment; do not use relocation to apply database changes.

## Phase 0A execution record

Completed structurally on 2026-08-15.

- Git-aware moves placed `app/`, `migrations/`, `Dockerfile`, `Makefile`, the backend README, `alembic.ini`, `pyproject.toml`, `uv.lock`, `docker/`, and `.dockerignore` under `backend/`.
- Root `docker-compose.yml` remains workspace orchestration. Its backend build contexts now use `./backend`; development mounts now point to `./backend/app`, `./backend/migrations`, and `./backend/alembic.ini`.
- Root `.env` remains the one authoritative local environment file. Compose uses `env_file: ./.env`; `backend/Makefile` explicitly exports `../.env` for backend-local Uvicorn/Alembic commands. No secret file was copied or moved.
- The former root backend README is now `backend/README.md`; a compact workspace README was added at root.
- `ARCHITECTURE_ANALYSIS.md` was absent and not tracked at execution time, so no historical-document move was performed.
- No Life source, migration, API, authentication, scheduler, bot, or frontend work was introduced.
- Automated relocation validation remains pending because repository instructions prohibit agents from running tests, builds, type checks, Docker validation, Alembic commands, and runtime checks. The planned commands above are for a developer or later explicitly authorized task.

## Phase 0B verification record

Completed on 2026-08-15 under the repository verification policy.

- Passed permitted read-only checks: clean `git status --short` before the Phase 0B documentation update, `git diff --check`, Git history/diff review, relocated-file topology review, stale-path scan, migration revision-chain inspection, and root `.env` tracking/topology inspection.
- The actual relocation commit contains 82 exact 100% renames and zero source/migration content edits. The following relocation patch changes only paths, Compose configuration, root-environment loading convention, guidance, and documentation; no Finance, Islamic, platform, API, scheduler, or migration behavior was intentionally changed.
- Verified statically: `backend/app/` and `backend/migrations/` exist; Alembic retains `script_location = migrations` and `prepend_sys_path = .`; Compose uses `./backend` contexts and relocated development mounts; Docker retains backend-relative container copies and `app.main:app`; the migration chain is `20260731_0001` → `20260801_0002` → `20260801_0003`; no Life migration/module or frontend directory exists.
- Root `.env` is the only discovered `.env`, is untracked, and is ignored. Compose references `./.env`; backend Make targets explicitly source `../.env`; backend documentation records the same direct-`uv` convention. Values were not printed.
- Not run because `AGENTS.md` prohibits tests, builds, type checks, Docker/Alembic/runtime validation: Python import command, Alembic `heads`/`current`, `docker compose config`, Docker dev build/start/health/down, and any external Telegram activity. These remain developer-pending before a deployment/release, not a reason to begin unrelated refactoring.
