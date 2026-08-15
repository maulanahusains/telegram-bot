# Life Implementation Plan

## Governing rules

- Read `README.md`, `STATE.md`, `DECISIONS.md`, and this file before production changes.
- Complete a phase’s criteria before starting the next. Update `STATE.md` and record decision changes.
- Current repository policy says agents must not run tests, linters, builds, formatters, type checks, or automated runtime validation unless the user explicitly changes that policy. “Verification” below describes work a developer/authorized future task should perform; it does not authorize it now.
- `life-docs/` remains at project root throughout every phase.
- No Life feature, table, migration, Mini App auth, or reminder table is part of Phase 0A/0B.

## Phase 0A — Isolated backend relocation

Objective: move only the existing backend from root into `backend/` and update path-sensitive backend/root-stack configuration. Follow `RELOCATION_PLAN.md` exactly.

Expected files/modules affected: existing backend-owned `backend/app/`, `backend/migrations/`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/alembic.ini`, `backend/Makefile`, backend README, and Docker support documentation; root `docker-compose.yml`, root README/ignore files as required by relocation. No Life module/files.

Migrations: none created, modified, or applied.

Verification: use only the planned commands in `RELOCATION_PLAN.md` when authorized by repository policy; otherwise perform read-only path/diff inspection and report skipped checks.

Prerequisites: none; DEC-013 is accepted.

Deliverable: `backend/` is independently runnable from its directory; root Compose still orchestrates PostgreSQL/backend/tunnel with explicit `backend/` paths; `life-docs/` stays root-level.

Out of scope: all Life features, frontend, schema changes, authentication, functional refactors, production behavior changes, Compose architecture redesign.

Completion criteria: no runtime/Alembic/Compose/Makefile path points to obsolete root backend paths; Git identifies moves cleanly; no Life migration exists.

## Phase 0B — Baseline verification and documentation update

Objective: verify relocation under authorized policy, correct documentation/commands, and record precise post-move state.

Expected files/modules affected: backend/root README(s), `life-docs/STATE.md`, `HANDOFF.md`, `RELOCATION_PLAN.md` verification record; fix only relocation defects discovered by verification.

Migrations: none.

Verification: commands listed in `RELOCATION_PLAN.md`; inspect `git status`/diff and migration head only if authorized.

Prerequisites: Phase 0A complete.

Deliverable: documented, reproducible post-relocation developer/deployment commands and verification status.

Out of scope: any Life persistence/API/frontend code.

Completion criteria: relocation checklist is closed or explicit blocker is recorded; `STATE.md` advances to Phase 1.

## Phase 1 — Mini App authentication and user-facing API foundation

Objective: add a secure user API boundary, server-side Telegram WebApp `initData` verification, global Telegram identity resolution, and short-lived authenticated session context.

Expected files/modules affected: under `backend/`, likely `backend/app/main.py`, new user auth/API route(s), config, auth/session services/repositories/models, shared exceptions/responses, Alembic migration; root/deployment config only when session origin requires it.

Migrations: application session table only if server-side PostgreSQL sessions are chosen. No Life domain tables.

Verification: signature validation fixtures, session expiry/revocation, unauthenticated API behavior, preservation of webhook/admin auth.

Prerequisites: Phase 0A/0B complete; review current Telegram WebApp verification specification; decide same-site cookie versus separate-origin token strategy.

Deliverable: verified `initData` resolves/upserts existing `telegram_users` and establishes authenticated API context under `/api/v1` (or accepted equivalent).

Out of scope: independent login, Life profile/features, Life bot, frontend feature screens.

Completion criteria: browser never supplies trusted owner ID; invalid/stale initData fails safely; existing bot ingress remains separate.

## Phase 1.5 — Minimal frontend foundation

Objective: obtain early Mini App/web UX feedback using real authenticated API bootstrap without feature-rich screens.

Expected files/modules affected: new root `frontend/` scaffold, TypeScript/tooling/configuration, Telegram SDK adapter/bootstrap, router/layout shell, auth bootstrap/fallback pages, minimal root Compose/deployment updates only if separately approved.

Migrations: none.

Verification: mocked Telegram SDK/bootstrap, auth bootstrap/error/fallback, responsive shell manual review, authenticated API integration.

Prerequisites: Phase 1 complete; frontend origin/session/CORS decision finalized.

Deliverable: responsive app shell with Today/Planner/Grocery/Progress/Settings navigation placeholders, Mini App auth bootstrap, and safe outside-Telegram fallback.

Out of scope: Life domain forms, fake local feature state, browser login.

Completion criteria: frontend authenticates only through backend and contains no canonical business logic.

## Phase 2 — Life profile, goals, and notification destinations

Objective: implement the first personal Life vertical slice: profile/settings, effective nutrition goals, and explicitly activated private/group/supergroup notification destinations.

Expected files/modules affected: `backend/app/modules/life/` module skeleton, profile/settings/destination models/repositories/services/schemas/API, standard module registration/composition, Alembic migration; frontend API client/types may receive non-feature bootstrap fields only.

Migrations: `life_profiles`, `life_nutrition_goals`, `life_notification_destinations` with owner, Life-bot, chat, activation/validation, and index/constraint design from `DATA_MODEL.md`.

Verification: owner isolation; timezone/goal validation; destination remains inactive until explicit owner activation; group visibility/validity checks; no chat owner path.

Prerequisites: Phase 1 complete and Life bot configuration/destination validation approach specified.

Deliverable: typed user API/application services for Settings, goals, and destinations; no reminders yet.

Out of scope: meal/workout/grocery/reminder tables, frontend rich settings screen if not needed for next slice.

Completion criteria: all canonical Life ownership references `telegram_users.id`; group destination is active only by explicit owner action and backend delivery validation.

## Phase 3 — Planner and reminder backend

Objective: implement one-time/recurring reminder definitions, occurrence state, durable PostgreSQL claim/executor semantics, and Planner API.

Expected files/modules affected: Life Planner models/repositories/services/schemas/API and executor composition under `backend/app/modules/life/`, configuration, health/logging additions only if warranted, Alembic migration.

Migrations: `life_reminders`, `life_reminder_occurrences`, indexes/unique constraints/lease fields. Do not generalize/modify Finance or Islamic schemas.

Verification: constrained recurrence/timezone/DST next-run behavior, 60-minute configurable grace default, no recurring bulk catch-up, concurrent claims/lease recovery, retry/permanent failure, inactive destination rejection, API idempotency.

Prerequisites: Phase 2 complete; one explicitly configured MVP executor deployment mode.

Deliverable: durable Planner user API/application services. Executor is safe to start but Telegram UX may remain minimal until Phase 4.

Out of scope: broker/Celery/Redis, complex recurrence, nutrition/fitness/grocery features.

Completion criteria: occurrence claims are transactionally safe, executor sends outside locks, and no in-memory timer is canonical state.

## Phase 3.5 — Planner frontend

Objective: make Planner a real vertical slice with structured reminder CRUD and destination selection.

Expected files/modules affected: `frontend/src/features/planner/`, settings/destination UI as needed, typed API hooks/forms/routes.

Migrations: none.

Verification: recurrence form validation, timezone/next-run presentation, activation warning for group destinations, API error/idempotency behavior, responsive manual review.

Prerequisites: Phase 3 API complete.

Deliverable: authenticated user creates/enables/disables/reschedules reminders through Mini App UI.

Out of scope: Telegram command CRUD, NLP scheduling, rich Today/Nutrition screens.

Completion criteria: all forms emit structured API payloads; frontend does not calculate canonical recurrence/ownership rules.

## Phase 4 — Telegram Life entry and reminder notification UX

Objective: add minimal Life runtime bot: `/start`, `/app`, optional simple `/today`, reminder delivery, and ownership-safe inline actions.

Expected files/modules affected: Life bot/router/formatting/callback adapter/factory under `backend/app/modules/life/`; bot provisioning documentation; no generic platform refactor unless required by evidence.

Migrations: none unless an occurrence action audit field is genuinely required.

Verification: command entry/app link, destination delivery, callback ownership in group, retry/failure behavior, bot-user status behavior.

Prerequisites: Phases 2–3.5 complete and Life bot configured through existing configuration flow.

Deliverable: Telegram is a notification/entry transport, never the principal feature UI.

Out of scope: complex command parser, natural-language input, group ownership semantics.

Completion criteria: a group callback cannot change another person’s data; personal action authorization always derives from Telegram actor/API session.

## Phase 5 — Nutrition, weight, and Fitness backend

Objective: create structured foods/templates/logs, weight history, workout schedules/completions, and Today/Progress-ready application/API services.

Expected files/modules affected: Life Nutrition/Fitness models/repositories/services/schemas/API and migrations under backend.

Migrations: foods, templates/items, meal logs/items, weight logs, workout schedules/completions with constraints/indexes in `DATA_MODEL.md`.

Verification: numeric validation, owner isolation, meal snapshots, local-date totals, goal history, workout completion idempotency, bounded histories.

Prerequisites: Phase 2 and API foundation complete.

Deliverable: deterministic backend user API for Nutrition/weight/Fitness; no external food data/AI.

Out of scope: automatic calorie adjustment, advanced workout programming, external nutrition API.

Completion criteria: backend calculates calories/protein/adherence; user examples are configurations, not code defaults.

## Phase 5.5 — Today, Nutrition, and Fitness frontend

Objective: expose the completed Nutrition/Fitness slice in responsive Mini App screens.

Expected files/modules affected: frontend Today/Nutrition/Fitness/Settings feature components, typed API hooks, charts/forms.

Migrations: none.

Verification: meal/weight/workout flows, Today quick actions, date/timezone display, error/loading states, mobile/desktop review.

Prerequisites: Phase 5 API complete.

Deliverable: Today shows server-calculated data and users manage foods/templates/logs/weight/workouts through structured forms.

Out of scope: food recognition, AI generation, predictive insights.

Completion criteria: UI does not duplicate totals or business rules.

## Phase 6 — Grocery and Progress backend

Objective: implement grocery lists/items/recurring items plus bounded Progress read models.

Expected files/modules affected: Life Grocery/Progress services/repositories/schemas/API and migrations under backend.

Migrations: grocery lists/items/recurring items and indexes.

Verification: ownership, bought idempotency, price/quantity validation, estimated totals, date range/query limits.

Prerequisites: Phase 5 complete.

Deliverable: typed Grocery/Progress API contracts.

Out of scope: inventory depletion/prediction, auto ordering, social/shared list features.

Completion criteria: all five primary frontend sections have a backend contract.

## Phase 6.5 — Grocery and Progress frontend

Objective: finish primary screen coverage using the Phase 6 API.

Expected files/modules affected: frontend Grocery/Progress feature UI, API hooks, routes/components.

Migrations: none.

Verification: list editing/bought state, simple estimate display, date filters/charts/history, responsive review.

Prerequisites: Phase 6 complete.

Deliverable: usable Grocery and Progress screens.

Out of scope: advanced analytics/prediction.

Completion criteria: screens use server read models and typed API errors.

## Phase 7 — Full integration and polish

Objective: complete cross-slice UX, onboarding, documentation, accessibility, and manual end-to-end flows.

Expected files/modules affected: scoped backend/frontend/docs/deployment files only as driven by integration findings.

Migrations: only additive changes justified by verified gaps.

Verification: end-to-end Mini App auth → Settings/destination → Planner → notification → inline action → Today/Progress; group visibility/authorization; restart durability.

Prerequisites: phases 1–6.5 complete.

Deliverable: compact MVP experience across web/Mini App/Telegram notification transports.

Out of scope: deferred/non-goal features in `PRODUCT.md`.

Completion criteria: no unresolved MVP blocker; docs and runbooks reflect actual architecture.

## Phase 8 — Hardening and deployment evolution

Objective: operationalize sessions, reminder executor, monitoring, and optional dedicated worker extraction based on real deployment evidence.

Expected files/modules affected: backend config/health/logging/worker entrypoint, root Compose/deployment manifests, frontend deployment config, docs/tests as needed.

Migrations: only additive operational/audit fields if justified.

Verification: restart/lease recovery, multi-executor safety, overdue-job observability, secret/session security, migration procedures.

Prerequisites: working MVP and real deployment/volume data.

Deliverable: explicit executor topology and operational runbook.

Out of scope: broker/Redis/Celery without demonstrated need.

Completion criteria: web replicas cannot accidentally create uncontrolled executor fleets; failures are visible/actionable.
