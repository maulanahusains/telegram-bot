# Life Product Plan

## Status legend

- **CONFIRMED REQUIREMENT** — supplied product direction.
- **FACT** — verified in current repository.
- **PROPOSAL** — recommended architecture/product choice awaiting confirmation where marked.
- **OPEN QUESTION** — cannot be decided from current requirements/code.

## Product goal

**CONFIRMED REQUIREMENT:** Life is a deterministic personal planning and tracking product, accessible through a responsive web application primarily launched as a Telegram Mini App, with a small Telegram bot for entry and notifications. It is not an AI assistant.

```text
validated structured user input
  → application service and deterministic rules
  → PostgreSQL
  → optional scheduled Telegram notification
```

The MVP gives one person a compact place to plan routines/reminders, record meals/weight/workouts, maintain a shopping list, and see Today/Progress. Personal data belongs to the person, never to the Telegram group where a bot happens to be installed.

## Confirmed MVP

### Telegram bot

- `/start` and `/app` open/describe the Mini App.
- Optional lightweight `/today` summary if it materially improves notification/entry UX.
- Deliver scheduled Telegram notifications and optional inline completion actions.
- Do not make commands the primary planning, food logging, or workout UI.

### Frontend information architecture

- **Today:** routine/reminder state, upcoming items, meal status, calorie/protein progress, workout status, quick completion.
- **Planner:** one-time/recurring reminders, routines, meal/workout schedules, enable/disable/reschedule, notification destination.
- **Grocery:** weekly list, recurring items, quantity, optional estimate, bought state, simple spending totals if naturally computed.
- **Progress:** weight history; calorie/protein and workout completion history.
- **Settings:** profile, nutrition goals, timezone, reminder defaults, notification destination, relevant preferences.

### Nutrition

- Persist per-user nutrition goals; the example body data/targets in the request are not defaults.
- User-created foods with serving, calories, and protein.
- User-created meal templates and scheduled meals.
- Daily meal logs and deterministic calorie/protein totals.
- Weight logs.
- No global nutrition database or external nutrition API required for MVP.

### Fitness

- Simple workout schedule with optional name/type and reminder time.
- Done/skipped completion state/history.
- No exercise-programming or coaching engine.

### Grocery

- Lists/items, quantities, optional estimated price, bought/unbought state, recurring items.
- No inventory depletion/prediction or automated ordering.

## Explicit non-goals / deferred work

**CONFIRMED REQUIREMENT:** exclude LLMs, AI chatbot behavior, NLP parsing, AI meal generation, image recognition, automatic inventory depletion, predictive ordering, complex exercise programming, social features, cross-bot analytics dashboard, autonomous calorie-target adjustment, email/password/Google login, Redis solely for cache, Celery solely for reminders, and microservices.

**PROPOSAL:** the weight-trend calorie suggestion is **post-MVP / first enhancement**. It needs at least 2–3 weeks of consistent weight data, an explicit baseline/trend rule, missing-data handling, and a settings/user acknowledgement model. If implemented later it must create a recommendation such as “2200 → 2300 kcal” and require Apply/Ignore; it must never silently modify a goal.

## Telegram and group behavior

**FACT:** current `telegram_users` gives one global identity per Telegram user, `bot_users` is bot membership, and `telegram_chats` stores chat identity (`app/platform/users/models.py`). Islamic uses `(bot_id, chat_id)` scopes because group data is intentional.

**CONFIRMED REQUIREMENT:** Life group/supergroup use is an optional notification destination and entry point. Personal meals, goals, weight, routines, and grocery data retain personal ownership. Opening the Mini App from a group should authenticate the launching Telegram user, not make the group owner. A selected group destination is simply a record used for outbound notifications.

**OPEN QUESTION:** Should MVP allow groups as selectable destinations, or initially only private chat? Group selection requires bot membership and the user must understand that reminders posted there are visible to group members. The conservative MVP is private chat default plus an explicit later group-destination setup flow.

## Major MVP UX flows

### Mini App authentication and first use

1. User opens Life from `/app`, menu/web-app button, private chat, or group.
2. Frontend receives Telegram WebApp launch data when inside Telegram.
3. Backend verifies the signed launch data and resolves the global Telegram identity.
4. Backend returns an authenticated API session.
5. Today loads. If no Life profile exists, Settings onboarding asks timezone/profile/nutrition/reminder defaults; no hardcoded goals are applied.

### Add and complete a reminder/routine

1. In Planner the user fills a structured form: title, one-time or recurring schedule, timezone/default, enabled state, destination.
2. Backend validates recurrence and computes durable next occurrence.
3. Executor claims a due occurrence and sends Telegram notification.
4. Inline action or Today action records completion/skipped status deterministically.

### Food/template and meal logging

1. User creates a custom food with explicit serving/macros.
2. User may combine foods into a named meal template.
3. User logs a structured meal/template for a date/time.
4. Today/Progress calculate totals from persisted log entries; the frontend does not own calculations.

### Workout and grocery

1. User schedules a simple workout and marks it done/skipped.
2. Grocery list can be created for a week, seeded from selected recurring items, edited, and checked off.
3. Any estimated total is the deterministic sum of current item estimate × quantity, not a prediction.

## Assumptions

- **FACT:** the current app uses PostgreSQL, async SQLAlchemy, FastAPI, Telegram webhooks, and database-backed bot configuration.
- **PROPOSAL:** all timestamp instants are stored in UTC; user timezone is stored as a validated IANA timezone.
- **PROPOSAL:** money uses integer minor units (e.g., IDR rupiah as an integer) and nutrition uses explicit decimals with documented units, avoiding floats for user-facing totals.
- **PROPOSAL:** reminder notification delivery initially targets Telegram only.

## Open product questions

1. Is a private Telegram chat sufficient as MVP notification destination, or must a group/supergroup be selectable immediately?
2. What notification types need inline actions: routine done, meal logged, workout done, reminder dismiss, or all of these?
3. What grace period makes a late one-time reminder useful rather than stale?
4. Is a grocery list always weekly, or should users select any date range at MVP?
5. Are meal logs one aggregate meal/template entry, or must individual food servings be editable from the first release? This plan supports editable entries because totals depend on them.
6. Is one timezone per Life profile sufficient for MVP? Proposed answer: yes; per-reminder timezone overrides remain optional.
