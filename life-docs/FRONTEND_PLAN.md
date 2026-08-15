# Frontend and Mini App Plan

## Recommendation

**IMPLEMENTED IN PHASE 1.5:** `frontend/` is a separate TypeScript React Vite SPA using React Router and TanStack Query. It is a small, conventional fit for a Telegram Mini App and normal responsive web UI; do not add Next.js/SSR unless public SEO/server rendering later creates a real need.

Use a small data-fetching layer such as TanStack Query for server state, native React state/context for local UI/session bootstrap, and form validation with a typed schema library selected during implementation. Do not introduce Redux or a complex global state stack for this MVP.

## Location and deployment

`frontend/` was created in Phase 1.5 as a root sibling of `backend/` and permanent `life-docs/`:

```text
project-root/
├── backend/
├── frontend/
└── life-docs/
```

**ACCEPTED / DEC-015:** keep frontend independently buildable/deployable, but deploy it same-origin with FastAPI for MVP: `app.example` serves the SPA and proxies `/api` to backend. The production Compose `frontend` service demonstrates this with Nginx; `frontend-dev` runs Vite and proxies `/api` to `app-dev`. A separate frontend origin remains possible only after a deliberate credentialed CORS/CSRF decision.

## Telegram SDK boundary

`frontend/src/app/telegram/webapp.ts` wraps Telegram WebApp access:

- Detect whether `window.Telegram?.WebApp` is available.
- Read raw `initData`; send only to backend auth endpoint over HTTPS.
- Call `ready()`, use theme/viewport values, and optionally expand UI without embedding business rules.
- Keep button/navigation integration and haptic calls isolated from pages/components.
- Do not trust client-reported Telegram user/chat identity; backend verification is authoritative.

The adapter returns a typed transient launch context with `isTelegram`, `initData`, platform/version, and color scheme. It calls `ready()` and `expand()` once at bootstrap and applies only a small set of Telegram theme variables. Pages work from API data and remain responsive outside Telegram.

## Browser fallback

**CONFIRMED REQUIREMENT:** independent browser login is not MVP. When outside Telegram:

- Render a responsive public shell explaining that sign-in currently requires opening Life in Telegram.
- Offer a deep-link/open-in-Telegram action configured from environment, if available.
- Do not fabricate a demo user or accept user IDs in query parameters.
- Keep routing/components normal enough that later browser auth can reuse them.

## Implemented frontend structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── api/             # typed relative HTTP client and auth calls
│   │   ├── auth/            # session-first Mini App bootstrap
│   │   ├── providers/       # TanStack Query provider
│   │   ├── router/          # /app and /tg/:launchingBot
│   │   └── telegram/        # one WebApp browser adapter
│   ├── modules/life/        # temporary authenticated Life-first shell only
│   ├── shared/components/   # small reusable state page
│   └── styles/
├── public/
├── package.json
└── README.md
```

Only boundaries needed by this thin slice were created. Future product folders own UI/query hooks/form models, but canonical validation/calculation rules remain backend-side.

## Routes and MVP pages

| Route | Page | Primary behavior |
| --- | --- | --- |
| `/` | redirect | routes to `/app` |
| `/tg/:launchingBot` | auth/bootstrap | session-first Mini App auth for a configured bot name |
| `/app` | auth/bootstrap | use an existing cookie session or show safe fallback |
| `/today` | Today | overview plus quick complete/log actions |
| `/planner` | Planner | reminder/routine CRUD, schedule/destination forms |
| `/grocery` | Grocery | lists, items, bought toggle, estimated total |
| `/progress` | Progress | date-bounded charts/lists for weight/macros/workouts |
| `/settings` | Settings | profile/timezone/goals/destinations/preferences |
| `/foods`, `/meal-templates`, `/meal-logs` | nested or modal routes | structured nutrition management |

**IMPLEMENTED IN PHASE 3.5:** `/app/planner` provides the first real vertical slice: list, structured create form, destination selection, one-time/daily/weekday recurrence fields, enable/disable, and delete. `/app/settings` provides compact profile/timezone, effective nutrition targets, destination candidates/activation, enablement, and default selection. Today/Grocery/Progress and foods/weight/Fitness screens remain deferred. Do not make Telegram viewport dimensions a required layout assumption.

## MVP interaction details

- **Today:** parallel fetch of aggregated response; quick actions call idempotent completion/log endpoints then invalidate Today/Progress queries.
- **Planner:** constrained recurrence form (daily/weekly + local time), show next occurrence/timezone and destination warning; no text-to-schedule parsing.
- **Nutrition:** food and template forms require numeric macros/quantities; meal log creates item snapshots through backend.
- **Grocery:** immediate bought toggle may use optimistic UI only after an idempotent API design is in place; reconcile server response.
- **Progress:** request a bounded range and render simple charts/tables. No predictive insights in MVP.
- **Settings:** first-run onboarding is a normal page/step sequence, not a blocking Telegram conversation.

## Session/data fetching

On startup, the frontend first fetches `GET /api/v1/me`. If that session is unauthenticated and the `/tg/:launchingBot` route has a valid configured-name-shaped hint plus Telegram raw `initData`, it sends exactly those two fields to `POST /api/v1/auth/telegram`, then invalidates/refetches `/me`. It relies on the Phase 1 HTTP-only cookie afterwards. Planner and Settings queries are owned by TanStack Query and invalidate server state after mutations; recurrence, ownership, and destination eligibility remain canonical backend rules. Handle session expiry by returning to bootstrap/open-in-Telegram state; never persist bot tokens, session tokens, or raw initData in browser storage beyond the immediate exchange.

## Testing plan when implementation begins

The repository has no frontend test toolchain yet. Per `AGENTS.md`, this phase does not run automated tests/builds. A future authorized test setup should cover the WebApp adapter with mocked `window.Telegram`, session-first bootstrap, auth error/fallback states, launch-route extraction, and logout query clearing.

## Telegram entry integration

**IMPLEMENTED IN PHASE 4:** Life uses `/tg/:launchingBot` consistently. Private chat `/app` buttons use Telegram’s `web_app` mechanism with the matching frontend route. Group/supergroup entry requires each configured Life bot’s Telegram Main Mini App to be configured in BotFather with that route; the bot sends its `t.me/{username}?startapp=life` direct link. The frontend still treats the route/start parameter as a hint only and submits raw `initData` to backend auth.
