# Current State

Last updated: 2026-08-16
Current phase: Phase 4 completed.
Status: Life profile/goals/destinations, durable Planner reminders, the Planner frontend vertical slice, and the Life Telegram entry/notification transport are implemented. Runtime validation remains developer-pending because repository policy prohibits agents from executing it.

## Completed

- Inspected the current FastAPI modular-monolith source, architecture documentation, migrations, Compose/Docker configuration, dependencies, API/error conventions, Finance module, Islamic module, platform identity/update layers, and scheduler loops.
- Created the root-level `life-docs/` planning and handoff workspace.
- Recorded proposed architecture, domain model, API, reminder, frontend, and implementation plans.
- Accepted confirmed product/architecture decisions, added group/supergroup MVP destinations, and superseded DEC-008 with DEC-013.
- Added a concrete isolated backend relocation plan and changed the roadmap to frontend-feedback vertical slices.
- Completed Phase 0A structural relocation: backend source, migrations, Python project metadata, Dockerfile, backend Makefile, backend README, Alembic configuration, Docker documentation, and Docker ignore rules now live in `./backend/`.
- Kept `life-docs/`, `docker-compose.yml`, `.env`, `.env.example`, and `.gitignore` at repository root. Root Compose now builds/mounts the relocated backend; root `.env` remains authoritative for Compose and is explicitly exported by `backend/Makefile` for backend-local runtime/Alembic commands.
- Completed Phase 0B permitted verification: the working tree was clean before this Phase 0B documentation update, `git diff --check` passed, and the relocation history was reviewed. The relocation commit contains 82 exact 100% renames with no source or migration-content edits; the follow-up changes are limited to paths, Compose, environment-loading convention, repository guidance, and documentation.
- Completed read-only stale-path and topology review: runtime Compose paths use `./backend`, Alembic remains backend-relative, `app.*` is still the Python import namespace, only root `.env` exists/is ignored/untracked, and no frontend or Life source/module/migration artifact exists.
- Completed Phase 1 platform authentication: reusable `backend/app/platform/auth/` validates Telegram Mini App `initData` against the selected enabled configured bot runtime, resolves/upserts `telegram_users`, refreshes/creates the launching bot membership, and establishes a reusable authenticated API context.
- Added platform-only `application_sessions` migration with hashed opaque session tokens, expiry, revocation, launching-bot context, and user foreign key. Added `POST /api/v1/auth/telegram`, `GET /api/v1/me`, and `POST /api/v1/auth/logout`; no Life route exists.
- Completed Phase 1.5 frontend foundation at root `frontend/`: React, TypeScript, Vite, React Router, TanStack Query, an application-owned official Telegram WebApp adapter, and minimal responsive light/dark-compatible styling.
- Implemented session-first bootstrap: `GET /api/v1/me` is attempted before a `POST /api/v1/auth/telegram` exchange. `/tg/:launchingBot` supplies only a public configured-bot lookup hint plus transient raw `Telegram.WebApp.initData`; `/app` safely reuses an existing session or renders a fallback.
- Added a temporary Life-first authenticated shell with minimal display information and logout only. No Today, Planner, Grocery, Progress, Settings, or Life domain UI/functionality exists.
- Added frontend Docker support: `frontend/Dockerfile` has Vite development and Nginx production targets; root Compose has `frontend-dev` and `frontend` profile services. The Nginx service demonstrates the accepted same-origin API/webhook/health/admin proxy topology.
- Accepted DEC-015 (same-origin frontend/API deployment) and DEC-016 (public multi-bot `/tg/:launchingBot` launch context).
- Completed Phase 2: registered `backend/app/modules/life/`, profile/goals/destination persistence, typed authenticated Life API, and migration `20260816_0005_life_profile_goals_destinations.py`.
- Accepted DEC-017: only a Life-bot webhook-observed user/chat candidate can be explicitly activated as a notification destination. No browser-supplied raw chat ID is accepted.
- Completed Phase 3: reminder definition/occurrence persistence, configured one-time grace, bounded retry, database claims/leases, constrained daily/weekly recurrence, owner-scoped Planner API, and migration `20260816_0006_life_planner_reminders.py`.
- Accepted DEC-018 for constrained recurrence, DST resolution, and explicit database-claimed executor lifecycle.
- Completed Phase 3.5: authenticated `/app/planner` and `/app/settings` routes, typed Life API client, structured Planner forms/list controls, and compact profile/goal/destination configuration UI.
- Completed Phase 4: `/start` and `/app`, context-aware Mini App entry buttons, privacy-aware reminder rendering, candidate observation, executor delivery integration, and owner-only Done/Skip callbacks.
- Accepted DEC-019 for private `web_app` versus group Main Mini App direct-link behavior.

## In progress

- No implementation work is in progress.

## Next

1. Begin Phase 5 — Nutrition, weight, and Fitness backend/API — only when explicitly authorized.
2. Before a deployment/release, have a developer run the deferred relocation, Phase 1, and Phase 1.5 import, Alembic, Compose, frontend build, migration, and local-stack smoke checks.

## Blockers

- No known structural blocker for Phase 5. Developer runtime verification of the relocated backend, Phase 1 auth flow, Phase 1.5 frontend/Compose integration, Phase 2/3 migrations/APIs/executor/frontend, and Phase 4 Telegram/BotFather configuration remains pending because repository policy prohibits this agent from executing it.
- Product implementation still needs the product owner to confirm the configured production grace-window value (60 minutes is the implemented default); this does not reopen accepted identity, reminder, session, launch-route, or same-origin decisions.

## Accepted planning decisions

- Life remains a modular-monolith module; canonical personal owner is `telegram_users.id`.
- No `application_users` table in MVP; bot users remain transport membership/state.
- Private/group/supergroup chats are explicitly activated notification destinations only, never owners.
- Telegram Mini App server-verified `initData` is MVP authentication entry.
- PostgreSQL-backed reminder definitions/occurrences/claims and one explicitly configured initial executor are accepted.
- No AI/LLM/NLP; REST/API and Telegram adapters share application services.
- One configurable one-time late-delivery grace window is accepted; planned initial default is 60 minutes, configuration-driven rather than hardcoded.
- Backend relocation to `backend/` is confirmed before Phase 1; `life-docs/` remains root-level.
- Platform Mini App authentication uses configured bot runtime verification, PostgreSQL-backed opaque sessions, and Secure/HttpOnly/SameSite cookies. FastAPI retains no CORS middleware because the MVP frontend/API topology is same-origin.
- Frontend/API same-origin deployment and public multi-bot `/tg/:launchingBot` launch context are accepted. Vite’s `/api` proxy is development-only; production frontend Nginx proxies public backend paths.

## Production structural changes already made

- Backend relocated to `./backend/` in Phase 0A. This was a path/configuration/documentation change only; the Python package remains `app` and no intended runtime business behavior was changed.
- Phase 1 added reusable platform auth/session infrastructure and one platform-only migration. Existing Telegram webhook/authentication, bot configuration, update idempotency, and bot modules were not refactored.
- Phase 1.5 added a root `frontend/` application plus root Compose frontend services and public frontend-port examples. It made no backend source, database, auth-contract, or Life feature changes.

## Life feature implementation

- Implemented through Phase 4: platform auth/frontend foundation; Life profile, effective-dated nutrition target configuration, explicit notification destinations; Planner definitions and durable occurrence executor; Planner/Settings UI; Life Telegram entry and group-safe quick-action transport. Foods/templates/logs, weight, Fitness, Grocery, Progress, and full Today remain unimplemented.

## Confirmed operational state

- Backend location: `./backend`
- Life feature implementation: implemented through Phase 4; runtime/manual verification remains pending
- Life migrations: `20260816_0005_life_profile_goals_destinations.py` and `20260816_0006_life_planner_reminders.py` generated; not applied by this agent
- Frontend: created at `./frontend`; Planner and compact Settings screens were added in Phase 3.5
- Canonical Life owner: `telegram_users.id`
- Group/supergroup notification destinations: MVP confirmed; explicitly activated destinations only
- Reminder architecture: PostgreSQL durable occurrence/claim model implemented; it runs only when one designated process enables `LIFE_REMINDER_EXECUTOR_ENABLED`

## Database migrations generated for Life

- `20260816_0005_life_profile_goals_destinations.py` — generated, not applied by this agent.
- `20260816_0006_life_planner_reminders.py` — generated, not applied by this agent.

## Verification status

- Passed permitted checks: initial `git status --short` (clean before Phase 1), static source/configuration/credential-boundary review, migration-chain inspection, official Telegram Mini App validation-specification review, frontend source/Docker/Compose/documentation inspection, and static Phase 2 ownership/API/migration review.
- Not run, per repository instruction: Python import startup, `uv`/Alembic commands, Compose rendering, npm/Vite build, Docker build/start/health smoke checks, tests, linters, formatters, type checks, and automated runtime validation.
- Repository inspection found no committed test files matching common `test`/`tests` patterns. Phase 1 test cases are documented in `backend/README.md`; Phase 1.5 test targets are documented in `FRONTEND_PLAN.md` for a developer/authorized runtime task.

## Important warnings for the next agent

- `life-docs/` is permanent at repository root; never place it inside `backend/` or `frontend/`.
- No LLM, AI chatbot, NLP intent parser, image recognition, or automatic natural-language interpretation belongs in Life MVP or this plan.
- Never use Telegram chat ID as canonical personal Life ownership. Islamic is chat-scoped by product design; Life is not.
- Group and supergroup destinations are confirmed MVP, but require explicit owner activation and backend delivery validation; bot installation alone is insufficient.
- Existing Finance/Islamic schedulers are in-process `asyncio` loops. Reuse their durable claim/locking ideas, not their module-specific schemas wholesale.
- Current repository instructions prohibit automated checks unless a later user request changes that policy.
- For local HTTP frontend development, set only the untracked root `.env` value `APPLICATION_SESSION_COOKIE_SECURE=false`; preserve the production-safe `true` default and never put tokens/initData in frontend configuration.
- Before enabling group app entry, configure each Life bot’s Main Mini App in BotFather to its public `/tg/{configured_bot_name}` route. Direct-link `startapp` is not an authorization mechanism.
