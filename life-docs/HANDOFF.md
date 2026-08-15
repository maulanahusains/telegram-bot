# Life Agent Handoff Procedure

## Resume checklist

1. Read `life-docs/README.md`, `STATE.md`, `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md` before touching production files.
2. Read the phase-relevant design docs: `ARCHITECTURE.md`, `DATA_MODEL.md`, `API_PLAN.md`, `REMINDERS.md`, `FRONTEND_PLAN.md`, and `PRODUCT.md` as applicable.
3. Read `RELOCATION_PLAN.md` before changing any root/backend paths or before running the deferred developer relocation checks. Phase 0B completed structural verification; its runtime/import/Alembic/Compose commands remain developer-pending under `AGENTS.md`.
4. Run read-only `git status --short` and `git diff --stat`; inspect any existing diff before assuming it belongs to your task. Preserve unrelated user work.
5. Use `STATE.md` to identify the current phase and confirm all prerequisites/completion criteria. Do not start a later phase early.
6. Inspect the current source because documents may be stale. Phase 0A relocated backend anchors under `backend/app/`, and Phase 0B verified the path/configuration diff. Run backend-local Python/Alembic work from `backend/` and use its Makefile so the authoritative root `../.env` is explicitly exported.

## During implementation

- Make only the changes authorized by the active phase and user request.
- Maintain the modular monolith; do not introduce a service/broker/cache without a recorded decision and evidence.
- Keep canonical Life ownership personal (`telegram_users.id`, DEC-002 accepted); never infer owner from a chat ID or client-submitted ID.
- Never make a REST endpoint invoke/simulate a Telegram router. Both transports call application services.
- Preserve `life-docs/` at repository root, outside both backend and frontend.
- Preserve deterministic structured behavior: no AI/LLM/NLP additions.
- Phase 1 platform auth belongs in `backend/app/platform/auth/`, never a product module. Use its authenticated-user dependency for user-facing APIs; never accept an owner ID as authorization proof.
- The Phase 1 session is an opaque HttpOnly cookie backed by `application_sessions`. Do not expose or log raw initData, session tokens, or bot credentials; use the configured launching runtime to verify Mini App data.
- Phase 1.5 frontend is at root `frontend/`. Its only trusted login flow is session-first `GET /api/v1/me`, then `POST /api/v1/auth/telegram` from `/tg/:launchingBot` with transient `Telegram.WebApp.initData`. Do not store initData or session data in browser storage, and do not add Life screens before their API/domain phase.
- Keep frontend API calls relative and same-origin. `frontend-dev` uses the Vite proxy only for local development; `frontend` uses Nginx to proxy public backend paths in the production Compose profile. Do not add backend wildcard CORS or a frontend token store.
- Phase 2 owns `backend/app/modules/life/` and migration `20260816_0005_life_profile_goals_destinations.py`. Notification destinations are activated only from the authenticated owner’s `life_destination_candidates` evidence; never add a raw chat-ID destination endpoint or treat a candidate as an activated destination.
- Phase 3 added `20260816_0006_life_planner_reminders.py`, constrained daily/weekly recurrence, and `LifeReminderExecutor`. Run the executor in exactly one explicitly configured process; preserve `SKIP LOCKED`, claim-token verification, and the rule that no transaction stays open during Telegram network I/O.
- Phase 3.5 added `/app/planner` and `/app/settings`. Keep forms narrow and typed; do not move schedule calculation, destination authorization, or user ownership into React state. Do not create placeholder UI for later Nutrition/Grocery/Progress work.
- Phase 4 makes `LifeBot` the thin Telegram transport. For groups, provision the bot’s Main Mini App in BotFather with the public `/tg/{configured_bot_name}` URL; do not replace it with a raw site link or private-only `web_app` button. Keep group notification text minimal and enforce callback ownership through `UserContext.internal_user_id`.

## Migrations and verification

- Before creating/changing a migration, inspect `backend/alembic.ini`, `backend/migrations/env.py`, latest revision, and the data-model section for the active phase.
- Phase 1 added `backend/migrations/versions/20260815_0004_platform_auth_sessions.py`. It is platform infrastructure, not a Life migration; do not add Life tables until the authorized Phase 2 work.
- Confirm migration head/order with the developer-approved Alembic command only when the task scope authorizes it. Do not assume migration has been applied merely because a file exists.
- This repository’s current `AGENTS.md` prohibits agents from running tests, linters, formatters, type checks, builds, and runtime validation unless a user explicitly changes that verification policy. Follow it; recommend relevant developer checks in handoff instead.
- The planning inspection found no committed test files. If tests are introduced, record their commands/coverage in `STATE.md` and phase completion criteria.

## Close each meaningful task

1. Update `STATE.md`: date, phase/status, completed/in-progress/next work, migrations produced/applied, verification performed/not performed, and warnings.
2. Add an entry to `DECISIONS.md` for architectural choices, alternatives, and consequences. Mark undecided choices Proposed; do not claim user approval.
3. Update the affected design doc when implementation supersedes its plan; keep entity/API names consistent.
4. Inspect `git diff --check`/test commands only if authorized by repository policy and task scope.
5. Report modified files, migration status, verification status, outstanding risks, and exact next phase.

## Guardrails

- Do not silently change accepted architecture; add a superseding DEC entry and obtain required approval.
- Do not mix directory relocation, broad refactors, and feature migrations in one change unless user explicitly scopes them together.
- Do not start later phases before current phase completion criteria pass.
- Do not add non-MVP features because an adjacent table/route seems convenient.
