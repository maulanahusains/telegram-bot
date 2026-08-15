# Life Implementation Plan

## Governing rules

- Read `README.md`, `STATE.md`, `DECISIONS.md`, and this file before production changes.
- Complete a phase’s criteria before starting the next. Update `STATE.md` and record decision changes.
- Current repository policy says agents must not run tests/linters/builds unless user scope changes it. “Tests” below are intended developer/approved future verification work, not authorization to run them now.
- `life-docs/` remains root-level throughout all phases.

## Phase 0 — Confirm decisions and prepare repository baseline

Objective: turn proposed architectural choices into accepted scope and choose repository-layout timing before code/migrations.

Expected files/modules affected: only `life-docs/DECISIONS.md`, `STATE.md`, and potentially planning docs. If relocation is approved now, create a separate dedicated relocation plan/PR before feature files.

Migrations: none.

Tests/verification: inventory existing tests (none found during planning), agree test tooling/commands and manual verification expectation; do not execute automated checks without authorization.

Prerequisites: user confirmation of canonical identity, destination scope, missed policy, session approach direction, and relocation timing.

Deliverable: accepted ADRs; a clean decision whether current root layout remains through Phase 3 or backend relocation precedes Phase 1.

Out of scope: Life code, frontend scaffold, API routes, migrations, scheduler.

Completion criteria: every blocking proposed decision is accepted/rejected/superseded; `STATE.md` names the next executable phase.

## Phase 1 — User authentication and application API foundation

Objective: add a secure user-facing API boundary and Telegram Mini App identity exchange without Life domain data.

Expected files/modules affected: likely `app/main.py`, new `app/api/...` user/auth route(s), `app/core/config.py`, new/extended auth/session service/repository/model files, `app/shared/exceptions.py`, `app/shared/responses.py`, migrations, and documentation. Exact layout depends on Phase 0 repository decision.

Migrations: application session table if server-side sessions are accepted; no Life feature tables yet. If a session model is not persisted, document revocation/expiry alternative before implementation.

Tests/verification: signature-validation unit tests using Telegram-compatible fixtures; session expiry/revocation tests; endpoint auth/ownership baseline tests; manual Mini App launch check once frontend exists.

Prerequisites: accepted session/deployment/CORS strategy and current Telegram WebApp verification specification review.

Deliverable: server-side verified Telegram initData → existing `telegram_users` resolution/upsert → short-lived authenticated API context; `/api/v1` (or accepted prefix) error/auth conventions.

Out of scope: independent browser login, frontend scaffold, Life profile/nutrition/reminder features, group ownership changes.

Completion criteria: no request can select owner ID; raw user ID is not trusted; unauthenticated requests fail consistently; existing webhook/admin authentication remains intact.

## Phase 2 — Life module and core personal persistence

Objective: create Life module boundaries, personal profile/settings, notification destination model, and minimal typed application/repository patterns.

Expected files/modules affected: `app/modules/life/__init__.py`, composition/bot skeleton, Life models/repositories/services/schemas, Life migration revision, possible module discovery/lifespan integration only through standard registration, API profile/settings/destination routes.

Migrations: `life_profiles`, optionally effective-dated `life_nutrition_goals`, `life_notification_destinations`, necessary indexes/FKs/checks.

Tests/verification: ownership isolation; timezone validation; destination ownership/default constraints; module factory/startup composition; migration upgrade/downgrade checks if authorized.

Prerequisites: Phase 1 complete and canonical owner decision accepted.

Deliverable: authenticated person can create/read/update Life profile/goals/destinations through transport-independent services/API.

Out of scope: reminders, meal/workout/grocery logic, frontend UI beyond any approved auth test client.

Completion criteria: no Life resource references chat as owner; no canonical stable data is put in generic `bot_user_states`/metadata JSONB.

## Phase 3 — Planner and durable reminder executor

Objective: implement constrained one-time/recurring definitions, occurrence state, database claims, executor lifecycle, and Telegram delivery adapter.

Expected files/modules affected: Life Planner models/repositories/services/schemas, Life migration, `app/modules/life/bot.py`, minimal Telegram adapter, configuration/health additions as warranted, Planner API routes.

Migrations: `life_reminders`, `life_reminder_occurrences`, indexes/constraints/claim fields; do not modify Finance/Islamic scheduler tables to make them generic.

Tests/verification: recurrence next-run across timezone/DST cases; one-time/recurrent transitions; duplicate/concurrent claim behavior; lease recovery; retry/permanent failure; destination disabled behavior; inline action ownership/idempotency; controlled restart simulation.

Prerequisites: Phase 2 complete; accepted missed policy and designated executor deployment mode.

Deliverable: an enabled reminder is durable across restart and can send a bounded/retry-aware Telegram notification; Planner API works without Telegram router simulation.

Out of scope: Celery/Redis/new broker, automatic grocery generation, complex recurrence, a dedicated worker deployment unless multi-replica deployment is already required.

Completion criteria: executor holds no DB lock while sending; DB constraints/claims make accidental concurrent executor starts safe; only one intentional executor is configured for MVP deployment.

## Phase 4 — Life Telegram entry and notification UX

Objective: add the deliberately small Life bot interface.

Expected files/modules affected: Life bot/router/formatting/Telegram callback code, Life module factory and possibly bot provisioning documentation.

Migrations: none unless callback/action audit requirements identified in Phase 3.

Tests/verification: `/start`, `/app`, optional `/today`, callback ownership, bot-user status behavior, group notification privacy behavior, outgoing message failure handling.

Prerequisites: Phase 3 complete; configured Life bot instance can be provisioned through existing admin/CLI flow.

Deliverable: Telegram is an entry/notification channel, not main CRUD interface.

Out of scope: command parser for meals/planner, natural-language intent parsing, complex chat flows.

Completion criteria: Life personal actions require owner verification; group chat never becomes the source of owner identity.

## Phase 5 — Nutrition, weight, and Fitness MVP backend/API

Objective: implement structured food/template/log, goals, weight, workout schedule/completion services and API.

Expected files/modules affected: Life Nutrition/Fitness models/repositories/services/schemas, API routes, migrations; Today aggregation service may start here.

Migrations: foods, meal templates/items, meal logs/items, weight logs, workout schedule/completion tables plus constraints/indexes in `DATA_MODEL.md` as scope demands.

Tests/verification: numeric/unit validation; owner isolation; immutable meal log nutrition snapshots; daily local-date totals; goal-effective-date selection; workout completion idempotency; bounded history pagination.

Prerequisites: Phases 1–3 complete.

Deliverable: API supports configured user foods/templates, meal/weight logs, calorie/protein summaries, workouts, and history.

Out of scope: external food API, AI/NLP logging, calorie auto-adjustment, advanced programming.

Completion criteria: Today/Progress calculations are server-side and deterministic; sample personal targets are not hardcoded.

## Phase 6 — Grocery MVP and Today/Progress read models

Objective: add grocery entities and finish compact frontend API read models.

Expected files/modules affected: Life Grocery models/repositories/services/schemas/API; Today/Progress aggregation services/routes; migrations.

Migrations: grocery lists/items/recurring items and indexes.

Tests/verification: list ownership; bought transition idempotency; quantity/price validation; estimated total; date-range/progress aggregation; query limits.

Prerequisites: Phase 5 complete.

Deliverable: complete backend MVP API for the five primary UI areas.

Out of scope: inventory depletion/prediction, auto ordering, social/shared grocery features.

Completion criteria: every primary frontend screen has a typed backend contract and no frontend-only canonical calculation is required.

## Phase 7 — Frontend foundation and MVP screens

Objective: create responsive Mini App/web frontend and integrate approved APIs.

Expected files/modules affected: new `frontend/` only if repository layout Phase 0 approved; root/Compose/deployment files only in a separately scoped infrastructure change; frontend docs/state updates.

Migrations: none.

Tests/verification: Telegram SDK adapter mock tests, auth bootstrap/fallback, form validation, API error states, responsive manual review, Mini App manual launch, end-to-end flows if test infrastructure is approved.

Prerequisites: backend phases exposing required APIs; final frontend origin/session/CORS deployment decision; repository relocation completed if chosen.

Deliverable: Today, Planner, Grocery, Progress, Settings responsive screens launched via Mini App and understandable outside Telegram.

Out of scope: non-Telegram login, native mobile app, AI functionality.

Completion criteria: no page needs a Telegram command parser; browser fallback is safe; API owns authorization/rules.

## Phase 8 — Hardening and deployment evolution

Objective: operationalize reminder delivery, security, and optional dedicated worker extraction based on real deployment needs.

Expected files/modules affected: configuration, health/metrics/logging, Docker/Compose/deployment manifests, worker entrypoint if needed, tests/docs.

Migrations: only additive operational/audit fields if evidence requires them.

Tests/verification: deploy with restart/lease recovery; multi-executor safety; overdue/reminder observability; secret handling; session security; migration rollback procedure.

Prerequisites: working MVP and real deployment/volume data.

Deliverable: explicit single-executor or worker topology, documented monitoring/runbook.

Out of scope: adding a broker/Redis/Celery without demonstrated need.

Completion criteria: deployment does not accidentally run uncontrolled executors per web worker; operational failures are visible/actionable.
