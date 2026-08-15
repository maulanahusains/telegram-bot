# Life Agent Handoff Procedure

## Resume checklist

1. Read `life-docs/README.md`, `STATE.md`, `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md` before touching production files.
2. Read the phase-relevant design docs: `ARCHITECTURE.md`, `DATA_MODEL.md`, `API_PLAN.md`, `REMINDERS.md`, `FRONTEND_PLAN.md`, and `PRODUCT.md` as applicable.
3. Run read-only `git status --short` and `git diff --stat`; inspect any existing diff before assuming it belongs to your task. Preserve unrelated user work.
4. Use `STATE.md` to identify the current phase and confirm all prerequisites/completion criteria. Do not start a later phase early.
5. Inspect the current source because documents may be stale; exact existing anchors include `app/core/lifespan.py`, `app/api/webhook.py`, `app/platform/users/`, `app/platform/updates/`, `app/modules/finance/`, and `app/modules/islamic/`.

## During implementation

- Make only the changes authorized by the active phase and user request.
- Maintain the modular monolith; do not introduce a service/broker/cache without a recorded decision and evidence.
- Keep canonical Life ownership personal (`telegram_users.id` if DEC-002 is accepted); never infer owner from a chat ID or client-submitted ID.
- Never make a REST endpoint invoke/simulate a Telegram router. Both transports call application services.
- Preserve `life-docs/` at repository root, outside both backend and frontend.
- Preserve deterministic structured behavior: no AI/LLM/NLP additions.

## Migrations and verification

- Before creating/changing a migration, inspect `alembic.ini`, `migrations/env.py`, latest revision, and the data-model section for the active phase.
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
