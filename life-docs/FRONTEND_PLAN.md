# Frontend and Mini App Plan

## Recommendation

**PROPOSAL:** use a separate TypeScript React frontend, most likely Vite + React + React Router, when frontend implementation starts. The current repository has no JavaScript tooling, frontend application, or SSR requirement. A Vite SPA is a small, conventional fit for a Telegram Mini App and normal responsive web UI; do not add Next.js/SSR unless public SEO/server rendering later creates a real need.

Use a small data-fetching layer such as TanStack Query for server state, native React state/context for local UI/session bootstrap, and form validation with a typed schema library selected during implementation. Do not introduce Redux or a complex global state stack for this MVP.

## Location and deployment

`frontend/` is not created in this task. Phase 0A relocates the backend first; then `frontend/` is created in Phase 1.5 as a root sibling of `backend/` and permanent `life-docs/`:

```text
project-root/
├── backend/
├── frontend/
└── life-docs/
```

Keep frontend independently buildable/deployable. Prefer a same-site reverse-proxy deployment (e.g., `app.example` serves frontend and proxies `/api` to backend) for Mini App cookie sessions and simple CORS. A separate frontend origin is possible but forces deliberate credentialed CORS/CSRF/token handling before implementation.

## Telegram SDK boundary

Wrap Telegram WebApp access behind a small frontend adapter, for example `src/platform/telegram.ts`:

- Detect whether `window.Telegram?.WebApp` is available.
- Read raw `initData`; send only to backend auth endpoint over HTTPS.
- Call `ready()`, use theme/viewport values, and optionally expand UI without embedding business rules.
- Keep button/navigation integration and haptic calls isolated from pages/components.
- Do not trust client-reported Telegram user/chat identity; backend verification is authoritative.

The adapter returns a typed launch context such as `{isTelegram, initData?, themeParams?}`. Pages work from API data and remain responsive outside Telegram.

## Browser fallback

**CONFIRMED REQUIREMENT:** independent browser login is not MVP. When outside Telegram:

- Render a responsive public shell explaining that sign-in currently requires opening Life in Telegram.
- Offer a deep-link/open-in-Telegram action configured from environment, if available.
- Do not fabricate a demo user or accept user IDs in query parameters.
- Keep routing/components normal enough that later browser auth can reuse them.

## Suggested frontend structure

```text
frontend/
├── src/
│   ├── app/                 # routing, providers, API/session bootstrap
│   ├── api/                 # typed HTTP client and endpoint hooks
│   ├── platform/            # Telegram WebApp adapter only
│   ├── features/
│   │   ├── today/
│   │   ├── planner/
│   │   ├── nutrition/
│   │   ├── fitness/
│   │   ├── grocery/
│   │   └── settings/
│   ├── components/          # reusable presentation components
│   ├── routes/              # page composition
│   └── styles/
├── public/
├── package.json
└── README.md
```

Feature folders own UI, query hooks, and form models, but canonical validation/calculation rules remain backend-side.

## Routes and MVP pages

| Route | Page | Primary behavior |
| --- | --- | --- |
| `/` | auth/bootstrap | verify Mini App session; redirect to Today or fallback |
| `/today` | Today | overview plus quick complete/log actions |
| `/planner` | Planner | reminder/routine CRUD, schedule/destination forms |
| `/grocery` | Grocery | lists, items, bought toggle, estimated total |
| `/progress` | Progress | date-bounded charts/lists for weight/macros/workouts |
| `/settings` | Settings | profile/timezone/goals/destinations/preferences |
| `/foods`, `/meal-templates`, `/meal-logs` | nested or modal routes | structured nutrition management |

Use bottom navigation or compact tab navigation for the five requested primary destinations on mobile, with accessible desktop layout at larger widths. Do not make Telegram viewport dimensions a required layout assumption.

## MVP interaction details

- **Today:** parallel fetch of aggregated response; quick actions call idempotent completion/log endpoints then invalidate Today/Progress queries.
- **Planner:** constrained recurrence form (daily/weekly + local time), show next occurrence/timezone and destination warning; no text-to-schedule parsing.
- **Nutrition:** food and template forms require numeric macros/quantities; meal log creates item snapshots through backend.
- **Grocery:** immediate bought toggle may use optimistic UI only after an idempotent API design is in place; reconcile server response.
- **Progress:** request a bounded range and render simple charts/tables. No predictive insights in MVP.
- **Settings:** first-run onboarding is a normal page/step sequence, not a blocking Telegram conversation.

## Session/data fetching

On startup, frontend detects Telegram, sends `initData` exactly to the auth exchange, then uses HTTP-only cookie or selected API credential according to Phase 1. It fetches `/auth/me`/profile bootstrap before feature routes. Handle session expiry by returning to bootstrap/open-in-Telegram state; never persist bot tokens or raw initData in local storage beyond immediate exchange.

## Testing plan when implementation begins

No frontend exists and repository inspection found no test suite. Phase 0 must establish test tooling expectations. At minimum, future implementation should include component/form tests for structured validation and integration tests for auth bootstrap/API error states; test Telegram adapter behavior with mocked `window.Telegram` rather than requiring Telegram in CI.
