# Architecture Decision Log

Dates use the planning-session date. **Proposed** entries require explicit user confirmation before implementation. Do not silently reinterpret an accepted decision; add a superseding entry instead.

## DEC-001 — Keep Life in the modular monolith

Status: Accepted
Date: 2026-08-15

Decision: Implement Life as one new module within the existing FastAPI/PostgreSQL modular monolith, with internal domain packages rather than microservices.

Context: FACT — `backend/app/core/module_discovery.py` discovers registered packages under `backend/app/modules/`; `backend/app/core/lifespan.py` composes one process/database runtime. Finance and Islamic already use this pattern.

Alternatives considered: separate services; separate database; a standalone frontend-only product.

Consequences: reuse database, identity, webhook, update, logging, and Telegram infrastructure. Maintain explicit module boundaries so Life does not couple its data to Finance or Islamic internals.

## DEC-002 — Canonical Life owner identity

Status: Accepted
Date: 2026-08-15

Decision: Life-owned personal tables should reference `telegram_users.id` as `owner_user_id` (or a semantically named foreign key to that table), not `bot_users.id` and not a chat ID.

Context: FACT — `telegram_users` is globally unique on `telegram_user_id`; `bot_users` is unique only per `(bot_id, user_id)` (`backend/app/platform/users/models.py`). Finance data references `bot_user_id`; Islamic data is chat-scoped. CONFIRMED REQUIREMENT — Life personal data must be a person’s data and may be accessed through Mini App/web and a Life bot, while a group is merely a notification destination.

Alternatives considered: `bot_users.id`; Telegram chat ID; a new application-user table immediately.

Consequences: one Life profile can be reused across Life Telegram interactions and Mini App sessions. Access through a Life bot still checks its `bot_users` membership/status. If future non-Telegram accounts are required, add a product identity table then and link it to `telegram_users`, rather than prematurely duplicating identities now.

## DEC-003 — Defer a new application-user table

Status: Accepted
Date: 2026-08-15

Decision: Do not add a separate application-user table in the MVP. Use existing global Telegram identity as canonical owner and defer a broader account abstraction until independent browser login or multi-identity linking is an approved requirement.

Context: CONFIRMED REQUIREMENT — Telegram Mini App authentication is primary; email/Google/password login is not MVP. FACT — no end-user web authentication or account table exists.

Alternatives considered: create `application_users` now; use only bot memberships.

Consequences: fewer migrations and no duplicate identity synchronization. Future authentication expansion must be a deliberate migration/ADR.

## DEC-004 — Group and chat semantics

Status: Accepted
Date: 2026-08-15

Decision: Model Telegram private-chat, group, and supergroup destinations separately from Life resources. A destination references a known Telegram chat, a sending Life bot configuration, and an owner-controlled activation/validation state. A group launch does not alter the authenticated person’s owner identity, and bot installation alone never activates a destination.

Context: CONFIRMED REQUIREMENT — groups are notification destinations/entrypoints, not canonical owners. FACT — `telegram_chats` already provides global chat identity; `islamic_scopes` is explicitly chat-owned.

Consequences: authorization must require ownership of the Life profile to activate/select a destination. Group/supergroup delivery viability must be validated with the bot’s actual membership/Telegram permission behavior before activation or delivery. This is MVP scope.

## DEC-005 — Mini App is the MVP authentication entry

Status: Accepted
Date: 2026-08-15

Decision: Authenticate the MVP frontend by server-side verification of Telegram WebApp `initData`, resolve/upsert the existing global Telegram user, and issue a short-lived backend API session/token. Do not trust a browser-supplied Telegram ID.

Context: CONFIRMED REQUIREMENT — Telegram Mini App authentication is primary. FACT — current authentication only verifies webhook secret tokens and an admin bearer key (`backend/app/api/webhook.py`, `backend/app/api/admin.py`).

Consequences: add a separate user-auth API boundary. Standalone browser behavior is a deferred unauthenticated fallback unless a future login option is approved.

## DEC-006 — PostgreSQL-backed reminder executor, initially co-located

Status: Accepted
Date: 2026-08-15

Decision: Build a generic Life reminder persistence/claim interface in PostgreSQL. Initially run one explicitly configured executor with the FastAPI deployment; keep its ownership/claim API independent so it can move to a separate worker process without domain changes.

Context: FACT — Finance and Islamic use 30-second in-process `asyncio` tasks with durable database state/claims (`backend/app/modules/finance/services.py`, `backend/app/modules/islamic/services.py`). No queue/broker/worker dependency is installed (`backend/pyproject.toml`).

Alternatives considered: Celery/Redis, APScheduler, a dedicated worker immediately, in-memory-only timers.

Consequences: no new infrastructure for MVP. Deployment must ensure a single designated executor until multi-replica behavior is validated; database claims must still make concurrent execution safe.

## DEC-007 — One Life module with internal domain boundaries

Status: Accepted
Date: 2026-08-15

Decision: Use `backend/app/modules/life/` with internal `planner`, `nutrition`, `fitness`, `grocery`, and shared Life application/transport code. Do not register these as independent runtime bot modules initially.

Context: CONFIRMED REQUIREMENT — these are logical product boundaries, not microservices. FACT — module registry operates at bot-module level; all Life features need shared profile, Today aggregation, API, and reminder integration.

Consequences: one Life bot runtime and coherent migrations while retaining subdomain ownership in source.

## DEC-008 — Defer root repository relocation

Status: Superseded by DEC-013
Date: 2026-08-15

Decision: Keep the existing root-level `app/`, `migrations/`, Docker, Compose, and Alembic paths through initial identity/Life backend work. Decide and execute a dedicated repository-preparation relocation before frontend implementation or before the first production Life migration, whichever occurs first.

Context: FACT — current Compose, Dockerfile, Makefile, Alembic, imports, and bind mounts all point to root-level paths. No frontend/CI is present. CONFIRMED REQUIREMENT — future shape may use `backend/`, `frontend/`, and root `life-docs/`.

Consequences: superseded because relocation is now confirmed before Phase 1. Retained for decision history only.

## DEC-009 — No AI or natural-language interpretation

Status: Accepted
Date: 2026-08-15

Decision: Life MVP behavior is deterministic structured input → validated application service → database/rules → notification. No LLM, AI assistant/chatbot, NLP parser, automatic meal generation, food image recognition, or autonomous recommendations.

Context: CONFIRMED REQUIREMENT.

Consequences: API/frontend forms and minimal commands are authoritative; all business rules remain explicit and testable.

## DEC-010 — Frontend must use user-facing API, never bot routers

Status: Accepted
Date: 2026-08-15

Decision: Telegram handlers and REST/Mini App endpoints call shared application services. REST must not simulate Telegram commands or invoke Telegram routers.

Context: CONFIRMED REQUIREMENT. FACT — current Finance and Islamic routers compose Telegram-specific parsing and presentation.

Consequences: extraction/adaptation of application use cases is required as Life is implemented.

## DEC-011 — MVP missed-reminder behavior

Status: Accepted
Date: 2026-08-15

Decision: one-time reminders are eligible for one late delivery only within a bounded configurable grace period; after that they become `missed` without a backlog blast. Recurring occurrences never bulk-catch up; missed occurrences are recorded/skipped and next occurrence is computed from the recurrence rule.

Context: FACT — Islamic currently has per-kind late windows and skips old reminders; Finance’s scheduler persists alert claims. Product has not specified the Life missed-notification UX.

Consequences: restart behavior is predictable and avoids sending obsolete reminders. Grace duration and user-visible missed status remain open product parameters.

## DEC-012 — `life-docs/` permanence

Status: Accepted
Date: 2026-08-15

Decision: retain `life-docs/` at project root permanently, sibling to `backend/` and `frontend/` if/when they exist.

Context: CONFIRMED REQUIREMENT.

Consequences: any future repository move must preserve this path and update links only as needed.

## DEC-013 — Isolated backend relocation before Phase 1

Status: Accepted
Date: 2026-08-15

Decision: Relocate the existing backend to `project-root/backend/` in Phase 0A, before Mini App authentication, Life migrations, Life modules, or frontend feature work. Keep `life-docs/` exactly at project root. Retain root-level `docker-compose.yml` as future stack orchestration and update it to build/mount `backend/` explicitly.

Context: CONFIRMED REQUIREMENT. FACT — `app/`, `migrations/`, `Dockerfile`, `pyproject.toml`, `uv.lock`, `alembic.ini`, `Makefile`, and backend README currently sit at root; Compose contains PostgreSQL, backend, and Cloudflare Tunnel service orchestration.

Alternatives considered: defer relocation; move Compose into backend; combine move with Life schema/features.

Consequences: relocation is an isolated, reviewable rename/path-update change with no Life migration. Root Compose can later add frontend service/networking while backend retains Docker/Python/Alembic ownership. See `RELOCATION_PLAN.md`.

## DEC-014 — Platform Mini App sessions use PostgreSQL and secure cookies

Status: Accepted
Date: 2026-08-15

Decision: Implement Telegram Mini App authentication under `backend/app/platform/auth/`. A request supplies a configured launching bot name and raw `initData`; the server resolves an enabled runtime, verifies the Telegram WebApp HMAC with that runtime's decrypted token, upserts `telegram_users`, resolves the launching bot's `bot_users` membership, and creates a short-lived opaque server session. Store only a SHA-256 session-token hash in `application_sessions`; issue the raw token only as a configurable Secure, HttpOnly, SameSite cookie scoped to `/api/v1`.

Context: CONFIRMED REQUIREMENT — auth must be reusable by Life, Finance, Islamic, and later frontend modules, with no new `application_users` table. FACT — PostgreSQL and encrypted database-backed bot credentials already exist; Redis, browser login, and a frontend origin do not. Telegram's current official Mini App documentation specifies an HMAC data-check-string derived from the launching bot token and `WebAppData`.

Alternatives considered: Life-local auth; unsigned browser-supplied Telegram ID; client-held bearer/JWT tokens; Redis sessions; password/OAuth login; a database session without a cookie.

Consequences: the authenticated application owner is always `telegram_users.id`, never a request-selected ID or `bot_users.id`. Bot membership is refreshed/created only for the verified launching bot and remains a transport permission check. Cookies assume same-site deployment; DEC-015 later confirms the same-origin frontend topology, so FastAPI still needs no CORS exception. Existing sessions become unusable if their launching bot is disabled or the relevant bot membership is no longer active.

## DEC-015 — Same-origin frontend/API deployment for the MVP

Status: Accepted
Date: 2026-08-15

Decision: The production frontend and FastAPI user API share one public origin. The frontend serves the SPA and routes `/api/*` to FastAPI; the browser uses relative API paths only. The root Compose production profile demonstrates this through the `frontend` Nginx service proxying API, webhook, health, and admin paths to `app`.

Context: CONFIRMED REQUIREMENT — Phase 1 uses Secure, HttpOnly, SameSite=Lax session cookies and must not weaken CORS/cookie policy for local convenience. FACT — the Phase 1 API has no CORS middleware. A same-origin route keeps cookie delivery and the Mini App API boundary simple.

Alternatives considered: separate frontend/backend origins with credentialed CORS; browser-held bearer tokens; enabling wildcard CORS.

Consequences: frontend code calls relative `/api/v1/*` paths with same-origin credentials. Vite proxies `/api` only in local development; the backend retains no CORS exception. A future separate-origin deployment requires a separate accepted CORS/CSRF decision before implementation.

## DEC-016 — Public multi-bot Mini App launch route

Status: Accepted
Date: 2026-08-15

Decision: Use `/tg/:launchingBot` as the public frontend Mini App launch route. The route parameter follows the existing configured bot-name grammar and is sent with raw `Telegram.WebApp.initData` to platform auth only after an existing session check fails. It is a routing/authentication lookup hint, never user identity or security proof.

Context: CONFIRMED REQUIREMENT — one frontend may be launched by Life, Finance, or Islamic/Muslimify bots. FACT — Phase 1 resolves the configured runtime by `launching_bot_name` and binds HMAC verification to that runtime’s encrypted credential.

Alternatives considered: hardcoded Life route; frontend-selected bot token; a no-context `/app` login route; a separate frontend per bot.

Consequences: `/tg/life`, `/tg/finance`, and `/tg/islamic` can share the application shell when configured. `/app` remains useful only for an already-valid cookie session; outside Telegram or without a launch context it shows a safe fallback.
