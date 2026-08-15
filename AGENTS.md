# Repository Guidelines

## Agent Operating Modes

### Assistant Mode (Default)

Use Assistant Mode unless the user explicitly asks for an implementation. In
this mode, inspect and analyze the repository according to the user's request,
explain findings and likely causes, identify risks and trade-offs, and give
actionable clues or hints for the developer.

Assistant Mode is read-only. Do not create, edit, delete, rename, or move files.
Requests to analyze, review, diagnose, explain, or recommend do not authorize
code changes. If implementation intent is ambiguous, remain in Assistant Mode
and describe what the developer should change.

### Implementor Mode (Explicit, Per Task)

Activate Implementor Mode only when the user clearly asks to implement a
change. Phrases such as "implement this," "change the code," "fix it directly,"
or an equivalent explicit instruction are sufficient; the exact phrase
"Implementor Mode" is not required.

In this mode, inspect the relevant code and make only the changes needed for the
requested task. Do not expand the scope without authorization. Implementor Mode
ends when that task is complete, and the agent returns to Assistant Mode for the
next request unless implementation is requested again.

Both modes may use read-only repository inspection. Database migrations,
starting services, or other stateful operations require explicit inclusion in
the user's requested scope.

## Verification Responsibility

Do not run tests, linters, formatters, type checks, builds, or automated runtime
validation. These checks are performed manually by the developer. After an
implementation, summarize the files and behavior changed and suggest relevant
manual checks without executing them.

## Graphify Maintenance

When source code under `backend/app/` changes, remind the developer once in the final
handoff to refresh the knowledge graph. This applies when the agent changes the
source in Implementor Mode or when the user states that they changed source code
during the conversation. Use this exact reminder:

> Reminder: source code berubah. Jalankan `/graphify . --update` untuk
> memperbarui knowledge graph.

Do not repeat the reminder in commentary updates, even when a task changes
multiple source files. Changes limited to documentation, `AGENTS.md`, Docker,
configuration, or migrations do not trigger it. The agent must not run the
Graphify update; refreshing the graph remains the developer's manual
responsibility. This reminder is not a test, lint, type check, build, or runtime
validation step.

## Project Structure & Module Organization

Application code lives in `backend/app/`. HTTP endpoints are under
`backend/app/api/`, shared infrastructure is in `backend/app/core/`, and reusable
response, exception, and type helpers belong in `backend/app/shared/`.
Platform-owned bot, update, and user behavior is grouped in
`backend/app/platform/`.

Add independently developed bots beneath `backend/app/modules/<bot_name>/`. Follow
`backend/app/modules/sample_bot/` for the expected router, handlers, services,
repositories, schemas, and models layout. Keep handlers thin: business rules
belong in services and persistence logic belongs in repositories.

Alembic configuration is in `backend/alembic.ini`, with migrations in
`backend/migrations/versions/`. Backend container configuration lives in
`backend/Dockerfile`; workspace orchestration lives in root `docker-compose.yml`.

## Developer Commands

These commands are references for the developer; agents must not execute them
unless a future user request explicitly changes the verification policy.

- `make -C backend install`: install locked Python 3.13 dependencies with `uv`.
- `make -C backend run`: run Uvicorn locally with auto-reload; the backend
  Makefile explicitly loads root `.env`.
- `make -C backend migrate`: upgrade the configured database to the latest revision.
- `make -C backend revision MESSAGE="add bot settings"`: generate an Alembic migration.
- `make -C backend docker-dev`: start PostgreSQL, the development app, and Cloudflare
  Tunnel using the `dev` Compose profile.
- `make -C backend docker-up`: build and start the production-profile containers.
- `make -C backend docker-down`: stop the Compose project.
- `make -C backend docker-dev-logs`: follow development app and tunnel logs.

## Coding Style & Naming Conventions

Use four-space indentation, Python type hints, and async APIs for database and
network operations. Name modules, functions, and variables in `snake_case`,
classes in `PascalCase`, and constants in `UPPER_SNAKE_CASE`. Preserve module
boundaries: bot modules should consume platform services instead of creating
their own database sessions, Telegram clients, or identity registration.

No formatter or linter is configured. Match the style and import organization
of nearby code.

## Commit & Pull Request Guidelines

Git history is unavailable in this workspace, so no existing message convention
can be verified. Use concise, imperative subjects, optionally scoped, such as
`users: prevent stale state writes`. Pull requests should explain the problem
and solution, link related issues, and call out migrations or configuration
changes. The developer is responsible for recording manual verification.

## Security & Configuration

Copy root `.env.example` to root `.env`; never commit `.env`, Telegram credentials,
Fernet keys, or Cloudflare tunnel tokens. Keep production secrets in a secret
manager. When running the tunnel in Compose, configure its origin as
`http://app-dev:8000`, not localhost.
