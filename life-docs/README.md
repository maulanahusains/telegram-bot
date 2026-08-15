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
- [FRONTEND_PLAN.md](FRONTEND_PLAN.md) — implemented frontend/Mini App foundation and next UI boundaries.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — executable phase-by-phase roadmap.
- [DECISIONS.md](DECISIONS.md) — architecture decision log.
- [STATE.md](STATE.md) — current project state and next action; update this during implementation.
- [HANDOFF.md](HANDOFF.md) — how a new agent resumes safely.
- [RELOCATION_PLAN.md](RELOCATION_PLAN.md) — exact Phase 0A backend-only relocation runbook.

## Planning Snapshot

**Recommended architecture:** retain the current PostgreSQL-backed FastAPI modular monolith. Add one `backend/app/modules/life/` module with internal Planner, Nutrition, Fitness, and Grocery domains. Expose transport-independent Life application services through both a small Life Telegram adapter and a new authenticated user API; do not route web requests through Telegram command routers.

**Confirmed canonical Life owner:** `telegram_users.id`, the existing global internal Telegram identity. `bot_users` remains appropriate for Life-bot membership, bot-specific state/status, and Telegram permissions; chat IDs are explicitly activated notification destinations only. Private chats, groups, and supergroups are MVP destination types; a bot being added to a group never selects or owns it.

**Confirmed reminder strategy:** PostgreSQL-backed reminder definitions plus durable occurrence/delivery claims and a database-locking executor. MVP runs one explicitly configured executor alongside the FastAPI deployment, while its composition remains independent enough to move to a dedicated process later. One-time reminders use one configurable late-delivery grace period (planned default: 60 minutes); recurring reminders do not bulk catch up.

**Frontend strategy:** Phase 1.5 created one responsive React/TypeScript/Vite SPA at root `frontend/`. Its primary routes are `/tg/:launchingBot` for multi-bot Telegram Mini App launches and `/app` for valid-session reuse. It first checks the HttpOnly platform session, then submits raw `initData` only to backend verification. Production uses an accepted same-origin frontend/API topology; normal browsers render a safe “open in Telegram” fallback. Independent browser login is deferred.

**Next implementation phase:** Phase 2 in `IMPLEMENTATION_PLAN.md` — Life profile, goals, and explicitly activated Telegram notification destinations. Phase 1.5 implemented only the frontend foundation and real platform-auth bootstrap; it did not create Life tables or feature screens.

**Remaining implementation-level questions:** exact grace-window value (60 minutes is planned) and group/private destination activation UX. These do not reopen the accepted ownership/reminder/session/relocation decisions. See `DECISIONS.md`, `PRODUCT.md`, and `RELOCATION_PLAN.md`.
