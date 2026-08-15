# Life Planning Workspace

This permanent, root-level directory is the durable handoff record for the Life product. It documents the intended architecture before implementation and must remain at `project-root/life-docs/`, always a sibling of any eventual `backend/` and `frontend/` directories. Never move it inside either application.

## Required workflow before production changes

Before changing production code for Life, an agent must read, in order:

1. `life-docs/README.md`
2. `life-docs/STATE.md`
3. `life-docs/DECISIONS.md`
4. `life-docs/IMPLEMENTATION_PLAN.md`

Then inspect `git status --short`, verify the current implementation phase, and read the relevant design documents before making only the work authorized by that phase. Update `STATE.md` after meaningful work and record an ADR in `DECISIONS.md` when an architectural decision changes. `HANDOFF.md` provides the operational resume procedure.

## Documents

- [PRODUCT.md](PRODUCT.md) — product scope, user experience, non-goals, and open product questions.
- [ARCHITECTURE.md](ARCHITECTURE.md) — verified current architecture and proposed incremental target architecture.
- [DATA_MODEL.md](DATA_MODEL.md) — proposed Life entities, ownership, constraints, and relationships; not migrations.
- [API_PLAN.md](API_PLAN.md) — planned authenticated Mini App/frontend API boundary.
- [REMINDERS.md](REMINDERS.md) — durable reminder model, executor, delivery, retry, and scale path.
- [FRONTEND_PLAN.md](FRONTEND_PLAN.md) — frontend/Mini App approach without a scaffold.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — executable phase-by-phase roadmap.
- [DECISIONS.md](DECISIONS.md) — architecture decision log.
- [STATE.md](STATE.md) — current project state and next action; update this during implementation.
- [HANDOFF.md](HANDOFF.md) — how a new agent resumes safely.

## Planning Snapshot

**Recommended architecture:** retain the current PostgreSQL-backed FastAPI modular monolith. Add one `app/modules/life/` module with internal Planner, Nutrition, Fitness, and Grocery domains. Expose transport-independent Life application services through both a small Life Telegram adapter and a new authenticated user API; do not route web requests through Telegram command routers.

**Recommended canonical Life owner:** `telegram_users.id`, the existing global internal Telegram identity. `bot_users` remains appropriate for Life-bot membership, bot-specific state/status, and Telegram permissions; chat IDs are notification destinations only. This is a **proposed** decision pending confirmation that Life must share one personal account across all current/future product surfaces.

**Reminder strategy:** PostgreSQL-backed reminder definitions plus durable delivery rows/claims and a database-locking executor. For the MVP it may run as one explicitly configured FastAPI-owned executor under the existing deployment assumption. Design the schema/claim interface so the same executor can move to a dedicated worker process later without changing reminder semantics.

**Frontend strategy:** create a separate responsive TypeScript frontend only after backend identity/API foundations are ready. Its primary MVP entry is Telegram Mini App `initData` verified by the backend; it must also render a safe “open in Telegram” fallback outside Telegram. Independent browser login is deferred.

**Next implementation phase:** Phase 0 in `IMPLEMENTATION_PLAN.md` — confirm the open product decisions, establish a baseline test strategy, and decide whether repository relocation to `backend/` occurs before any Life imports/migrations. Do not create Life tables or feature code before that phase completes.

**Unresolved decisions requiring user confirmation:** whether canonical Life data must be shared with Finance/other bots under one product account; the exact MVP missed-reminder policy; whether reminders need group destinations in MVP; and whether to relocate the backend before frontend work. See `DECISIONS.md` and `PRODUCT.md`.
