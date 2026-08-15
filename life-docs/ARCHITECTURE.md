# Life Architecture Plan

## Verified current architecture

### Facts

- `backend/app/main.py` registers `/health`, `/admin/*`, and `POST /webhook/{bot_name}`. There is no user-facing product API, API version prefix, CORS middleware, or user browser auth.
- `backend/app/core/lifespan.py` creates one `ApplicationContainer`, discovers `backend/app/modules/*`, loads database-configured bot instances, verifies/synchronizes webhooks, starts bot background work, and closes HTTP/database resources on shutdown.
- `backend/app/core/registry.py` defines `BaseBot`, module factories, and runtime registries. Module packages register by name in their `__init__.py` files.
- `backend/app/platform/users/models.py` has global `telegram_users`, global `telegram_chats`, per-bot `bot_users`, and per-bot-user JSONB conversation state. `UserContextService` upserts/returns these during webhook processing.
- `backend/app/platform/updates/` provides database-backed `(bot_id, update_id)` idempotent claims, leases, and bounded attempts.
- `backend/app/modules/finance/` is per `bot_user_id`; its router is Telegram-specific while `FinanceService` and `FinanceRepository` hold most invariants/persistence.
- `backend/app/modules/islamic/` is intentionally per `(bot_id, chat_id)` and persists prayer schedules and Quran state; it has a module-local external API adapter.
- Finance and Islamic each start an `asyncio` scheduler task in `BaseBot.start()`. Both persist operational state in PostgreSQL but have no separate worker process.

## Target architecture

**ACCEPTED:** retain a modular monolith and introduce `backend/app/modules/life/` as one registered bot module after Phase 0A relocation. It internally owns Planner, Nutrition, Fitness, and Grocery packages/domain boundaries. It should not become four independently registered bots or microservices.

```mermaid
flowchart LR
    TG[Telegram webhook / bot] --> TH[Life Telegram adapter]
    MA[Telegram Mini App] --> AU[/API auth boundary/]
    WEB[Responsive browser UI] --> AU
    AU --> API[Life REST API]
    TH --> USE[Life application services]
    API --> USE
    USE --> REPO[Life repositories]
    REPO --> DB[(PostgreSQL)]
    EXEC[Durable reminder executor] --> REPO
    EXEC --> OUT[TelegramBotClient]
    OUT --> TGAPI[Telegram Bot API]
```

The API must never call a Telegram router or simulate a command. Telegram adapters translate Telegram update/callback data into typed use-case requests; REST adapters validate JSON into equivalent requests. Application services own rules, transaction boundaries, ownership checks, scheduling calculations, and output values. Repositories own queries and persistence. Telegram presentation (HTML/buttons) and frontend presentation remain transports.

### Proposed Life source boundaries

```text
backend/app/modules/life/
├── __init__.py                 # register `life` factory only
├── bot.py                      # BaseBot lifecycle + small Telegram facade
├── telegram_router.py          # /start, /app, optional /today, inline actions
├── services/                   # cross-domain Today + application use cases
├── planner/                    # reminder/routine definitions, occurrences, destinations
├── nutrition/                  # goals, foods, templates, meal logs, weight
├── fitness/                    # workout schedules and completion history
├── grocery/                    # lists, recurring items, list items
├── repositories/               # explicit session-bound queries, possibly subdomain files
├── models.py or models/        # SQLAlchemy models; choose one repository-consistent style
├── schemas.py or schemas/      # typed service/API values, not Telegram payloads
└── api.py                      # Life REST router only when user API foundation exists
```

This is a proposal, not a requirement to create every folder upfront. Start with only the boundaries a phase needs; the central rule is one Life module with internal ownership and no circular access to Finance/Islamic private tables.

## Identity and authorization architecture

**ACCEPTED:** use `telegram_users.id` as Life’s `owner_user_id`. This existing internal identity is global across configured bots, unlike `bot_users.id` which is membership within a single bot. No new application-user table is necessary while Telegram Mini App is the only end-user login.

`bot_users` remains meaningful for Life Telegram transport: it establishes the user’s membership/status/role in the Life bot and supplies transient bot state. It must not become the foreign key for canonical Life resources, because it would tie a person’s profile to a particular Life bot configuration and complicate web access.

```mermaid
flowchart TD
    TU[telegram_users.id
global Telegram identity] --> LP[life_profiles.owner_user_id]
    TU --> BU[bot_users
Life bot membership/status]
    TC[telegram_chats] --> ND[life_notification_destinations.chat_id]
    LP --> ND
    LP --> DOM[Life personal resources]
    BU --> TS[Transient Telegram state only]
```

Every Life API query receives an authenticated `owner_user_id` from the server-side session, never from a request body/path alone. Every repository query writes/filter by that owner. Notification destinations are only selected by their owning profile. For group destinations, check that the configured Life bot can legitimately send to the chat and require explicit user action/consent in UI.

## Mini App authentication architecture

```mermaid
sequenceDiagram
    participant U as Telegram user
    participant M as Mini App frontend
    participant A as FastAPI auth endpoint
    participant D as PostgreSQL
    U->>M: Open web app (private/group/menu)
    M->>A: POST signed WebApp initData
    A->>A: Validate HMAC, bot token binding, auth_date freshness
    A->>D: Resolve/upsert telegram_users row
    A->>A: Create short-lived authenticated session/token
    A-->>M: Session + platform identity bootstrap
    M->>A: Authenticated /api/v1/life/* calls
    A->>D: Enforce owner_user_id on every resource
```

**IMPLEMENTED IN PHASE 1:** `backend/app/platform/auth/` owns the reusable auth service, session repository/model, schemas, and authenticated-user dependency. `POST /api/v1/auth/telegram` validates raw signed `initData` against an enabled launching runtime selected by configured bot name. It parses the query string once, rejects duplicates/malformed data, calculates Telegram's `WebAppData` HMAC using the runtime's decrypted bot token, compares hashes in constant time, checks configurable `auth_date` freshness/skew, and only then parses the Telegram user. It never logs or stores raw initData or a bot token.

**IMPLEMENTED IN PHASE 1:** a PostgreSQL `application_sessions` table stores a SHA-256 hash of an opaque random session token, the global user, launching bot, expiry, last-seen, and revocation timestamps. The raw token is issued only in a configurable Secure/HttpOnly/SameSite cookie scoped to `/api/v1`; `GET /api/v1/me` and future user APIs derive internal identity through the platform dependency. New login rotates active sessions for that user+launching-bot pair; logout revokes the stored row. No raw token, raw initData, or bot credential is persisted.

**IMPLEMENTED IN PHASE 1.5 / DEC-015 and DEC-016:** the React frontend’s `/tg/:launchingBot` route first checks `/api/v1/me`; only on a 401 does it send that public bot-name hint and transient raw `Telegram.WebApp.initData` to platform auth. The frontend uses only relative `/api/v1/*` paths and `credentials: "same-origin"`. Root Compose provides production Nginx routing and a Vite development proxy; FastAPI retains no CORS middleware.

Opening from different chats changes launch context, not `owner_user_id`. The backend may record/validate an optional launch chat only to preselect a notification destination after authorization. When opened outside Telegram, show an unauthenticated “Open in Telegram” page; independent login is deferred.

## Reminder executor architecture

See [REMINDERS.md](REMINDERS.md) for detail. The target is PostgreSQL source-of-truth schedules plus due occurrence/delivery claims. An executor polls due rows, claims with transactional locking, sends through the injected Life bot Telegram client, and records success/failure/retry. No in-memory timer is canonical.

For MVP, a FastAPI-owned executor can reuse the explicit lifecycle pattern in `backend/app/core/lifespan.py`/`BaseBot.start()`, **but deployment must designate only one executor**. Claiming must be safe even if two start accidentally. Future deployment can run the same executor class as a dedicated process without changing data model/business rules.

## Backend/frontend responsibilities

| Concern | Backend | Frontend |
| --- | --- | --- |
| Authentication proof | Verify Telegram initData; create session | Acquire/initiate auth; never verify signatures itself |
| Rules/totals/scheduling | Canonical calculations and validation | Present results and structured forms |
| Resource ownership | Authorize via server identity | Never select owner ID |
| Notifications | Compute/claim/deliver/record | Configure destination/preferences |
| Telegram command UI | Minimal command/callback transport | Not applicable |
| Responsive UX | JSON contracts | Today/Planner/Grocery/Progress/Settings |

## Eventual repository layout

**FACT:** Phase 0A relocated backend-owned files to `backend/`: `backend/app/`, `backend/migrations/`, `backend/Dockerfile`, `backend/alembic.ini`, and `backend/Makefile`. Root `docker-compose.yml` remains workspace orchestration and uses `./backend` as the backend build context. Phase 1.5 added `frontend/` and optional production/development Compose services; no CI configuration exists.

**ACCEPTED:** execute the dedicated backend-only move first, in Phase 0A, before Phase 1 authentication or any Life migration. See `RELOCATION_PLAN.md`; no Life feature code belongs in the move.

```text
project-root/
├── backend/                    # current backend root contents after deliberate move
├── frontend/                   # current independently buildable responsive application
├── life-docs/                  # permanent, stays root-level
├── docker-compose.yml          # optional root orchestration after deliberate decision
└── README.md                   # root-level entry documentation
```

The relocation checklist updates Docker build contexts, Compose volumes/commands, Alembic paths, Makefile working directories, `.env` loading, documentation, deployment scripts, and import/run commands. Git will see a large rename; isolate it in its own commit/PR and do not combine it with a schema migration. A root Compose remains appropriate to orchestrate backend/frontend/PostgreSQL, while each app retains its own build configuration.
