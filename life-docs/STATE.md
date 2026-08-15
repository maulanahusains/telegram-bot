# Current State

Last updated: 2026-08-15
Current phase: Phase 1 completed.
Status: Platform Telegram Mini App authentication, global Telegram identity resolution, and authenticated user API/session foundation are implemented. Runtime validation remains developer-pending because repository policy prohibits agents from executing it.

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

## In progress

- No implementation work is in progress.

## Next

1. Begin Phase 1.5 — minimal frontend foundation and real Mini App auth bootstrap — only when explicitly authorized.
2. Before a deployment/release, have a developer run the deferred relocation and Phase 1 import, Alembic, Compose, migration, and local-stack smoke checks.

## Blockers

- No known structural blocker for Phase 1.5. Developer runtime verification of the relocated backend and Phase 1 auth flow remains pending because repository policy prohibits this agent from executing it.
- Product implementation still needs exact grace-window value, destination activation UX, and final frontend reverse-proxy/origin deployment detail; these do not block Phase 1.5 preparation.

## Accepted planning decisions

- Life remains a modular-monolith module; canonical personal owner is `telegram_users.id`.
- No `application_users` table in MVP; bot users remain transport membership/state.
- Private/group/supergroup chats are explicitly activated notification destinations only, never owners.
- Telegram Mini App server-verified `initData` is MVP authentication entry.
- PostgreSQL-backed reminder definitions/occurrences/claims and one explicitly configured initial executor are accepted.
- No AI/LLM/NLP; REST/API and Telegram adapters share application services.
- One configurable one-time late-delivery grace window is accepted; planned initial default is 60 minutes, configuration-driven rather than hardcoded.
- Backend relocation to `backend/` is confirmed before Phase 1; `life-docs/` remains root-level.
- Platform Mini App authentication uses configured bot runtime verification, PostgreSQL-backed opaque sessions, and Secure/HttpOnly/SameSite cookies; CORS remains unset until frontend deployment is decided.

## Production structural changes already made

- Backend relocated to `./backend/` in Phase 0A. This was a path/configuration/documentation change only; the Python package remains `app` and no intended runtime business behavior was changed.
- Phase 1 added reusable platform auth/session infrastructure and one platform-only migration. Existing Telegram webhook/authentication, bot configuration, update idempotency, and bot modules were not refactored.

## Life feature implementation

- Not started. No Life models, migrations, profile/nutrition/reminder/planner/workout/grocery feature code, Life Telegram bot code, frontend application, or AI/LLM functionality exists. Mini App authentication and user-facing API routes exist only as reusable platform infrastructure.

## Confirmed operational state

- Backend location: `./backend`
- Life feature implementation: not started
- Life migrations: none (`application_sessions` is platform auth infrastructure)
- Frontend: not created
- Canonical Life owner: `telegram_users.id`
- Group/supergroup notification destinations: MVP confirmed; explicitly activated destinations only
- Reminder architecture: PostgreSQL durable occurrence/claim model confirmed; one explicitly configured initial executor when Phase 3 is authorized

## Database migrations already applied/generated for Life

- None.

## Verification status

- Passed permitted checks: initial `git status --short` (clean before Phase 1), static source/configuration/credential-boundary review, migration-chain inspection, no-Life/no-frontend artifact scan, and official Telegram Mini App validation-specification review.
- Not run, per repository instruction: Python import startup, `uv`/Alembic commands, Compose rendering, Docker build/start/health smoke checks, tests, linters, formatters, type checks, and automated runtime validation.
- Repository inspection found no committed test files matching common `test`/`tests` patterns. Phase 1 test cases and deferred commands are documented in `backend/README.md` and `RELOCATION_PLAN.md` for a developer/authorized runtime task.

## Important warnings for the next agent

- `life-docs/` is permanent at repository root; never place it inside `backend/` or `frontend/`.
- No LLM, AI chatbot, NLP intent parser, image recognition, or automatic natural-language interpretation belongs in Life MVP or this plan.
- Never use Telegram chat ID as canonical personal Life ownership. Islamic is chat-scoped by product design; Life is not.
- Group and supergroup destinations are confirmed MVP, but require explicit owner activation and backend delivery validation; bot installation alone is insufficient.
- Existing Finance/Islamic schedulers are in-process `asyncio` loops. Reuse their durable claim/locking ideas, not their module-specific schemas wholesale.
- Current repository instructions prohibit automated checks unless a later user request changes that policy.
