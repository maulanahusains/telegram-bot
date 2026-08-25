# Graph Report - .  (2026-08-25)

## Corpus Check
- 78 files · ~68,508 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1741 nodes · 5065 edges · 139 communities (66 shown, 73 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 423 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- GitLab Formatting
- Life API Services
- Islamic API Client
- Finance Bot Runtime
- Database Infrastructure
- Telegram Client Infrastructure
- HTTP Health Webhooks
- Life Domain Services
- Life Persistence
- Deployment Documentation
- Admin API
- Frontend Dependencies
- Module Discovery Registry
- Authentication API
- Application Settings
- GitLab API Client
- Life Frontend Shell
- Reminder Executor
- Application Lifespan
- User Authentication
- Life Data Models
- TypeScript App Config
- GitLab Design Concepts
- GitLab Bot Router
- GitLab Client Schemas
- Life Frontend API Types
- GitLab Bot
- Reminder Persistence
- Frontend App Router
- Grocery Frontend
- TypeScript Node Config
- Life Bot
- Session Persistence
- Life User Guide
- Planner Frontend
- Bot Registry
- Goal Recommendations
- Bot Persistence
- Manual Script Runner Plan
- Settings Frontend
- GitLab Webhook API
- Project Selector Plan
- CI Job Mapping
- GitLab Ops Runbook
- Repository Guidelines
- Islamic Migration
- Update Handler
- Goal Preferences
- Frontend HTML Entry
- TypeScript Project Config
- Application Package
- User Context
- Repository Package
- Sample Bot Webhook
- Bot Configuration
- Platform Package
- Update Domain
- User Domain
- Shared Utilities
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- HTTP Framework Types
- Security HTTP Types
- Database Session Types
- Web Framework Types
- Shared Generic Types
- Web Framework Types
- HTTP Response Types
- HTTP Request Types
- Bot Context Types
- Shared Generic Types
- Validation Model Types
- Secret Configuration Types
- Web Framework Types
- Date Domain Types
- Enum Domain Types
- Date Domain Types
- Database Session Types
- Date Domain Types
- Date Domain Types
- Enum Domain Types
- Database Session Types
- Date Domain Types
- Database Session Types
- Enum Domain Types
- Database Session Types
- Validation Model Types
- Secret Configuration Types
- Enum Domain Types
- Database Session Types
- DateTime Domain Types
- Enum Domain Types
- Exception Types
- Enum Domain Types
- Shared Generic Types
- Database Session Types
- DateTime Domain Types
- Validation Model Types
- Shared Generic Types
- Bot Context Types
- DateTime Domain Types
- Shared Generic Types
- Validation Model Types
- Shared Generic Types
- Validation Model Types
- Exception Types
- DateTime Domain Types
- Validation Model Types
- HTTP Client Types
- Secret Configuration
- Exception Type
- Validation Utility
- Product Documentation
- Error Handling Type

## God Nodes (most connected - your core abstractions)
1. `LifeService` - 108 edges
2. `GitlabOpsService` - 82 edges
3. `GitlabOpsRepository` - 58 edges
4. `Settings` - 55 edges
5. `LifeRepository` - 54 edges
6. `_service()` - 53 edges
7. `IslamicService` - 50 edges
8. `TelegramBotClient` - 45 edges
9. `FinanceService` - 45 edges
10. `GitlabApiClient` - 39 edges

## Surprising Connections (you probably didn't know these)
- `API-Only Pipeline Creation` --semantically_similar_to--> `API-Only Pipeline Source Filter`  [INFERRED] [semantically similar]
  docs/gitlab-ops-manual-script-runner-plan.md → .gitlab-ci.yml
- `GitLab Event Executor` --semantically_similar_to--> `Life Reminder Executor`  [INFERRED] [semantically similar]
  docs/gitlab-ops-bot-plan.md → backend/README.md
- `Configured Manual GitLab Job` --semantically_similar_to--> `Development Operation Job`  [INFERRED] [semantically similar]
  docs/gitlab-ops-manual-script-runner-plan.md → .gitlab-ci.yml
- `Configured Manual GitLab Job` --semantically_similar_to--> `Production Operation Job`  [INFERRED] [semantically similar]
  docs/gitlab-ops-manual-script-runner-plan.md → .gitlab-ci.yml
- `Docker Deployment` --references--> `Workspace Compose Orchestration`  [EXTRACTED]
  backend/README.md → docker-compose.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Backend Telegram Update Request Flow** — backend_readme_generic_webhook_api, backend_readme_runtime_bot_registry, backend_readme_update_idempotency, backend_readme_user_context_service, backend_readme_bot_context, backend_readme_postgresql [EXTRACTED 1.00]
- **GitLab Webhook Processing Flow** — docs_gitlab_ops_bot_plan_gitlab_webhook_inbox, docs_gitlab_ops_bot_plan_gitlab_event_normalizer, docs_gitlab_ops_bot_plan_gitlab_event_executor, docs_gitlab_ops_bot_plan_notification_subscriptions, docs_gitlab_ops_bot_plan_audit_events [EXTRACTED 1.00]
- **Life Bot and Mini App Product Flow** — docs_panduan_penggunaan_life_bot_life_bot, docs_panduan_penggunaan_life_bot_life_mini_app, docs_panduan_penggunaan_life_bot_planner_reminders, docs_panduan_penggunaan_life_bot_grocery_lists, docs_panduan_penggunaan_life_bot_progress_tracking [EXTRACTED 1.00]

## Communities (139 total, 73 thin omitted)

### Community 0 - "GitLab Formatting"
Cohesion: 0.06
Nodes (50): action_markup(), branch_matches(), deployment_text(), mr_text(), pipeline_text(), project_text(), push_text(), Any (+42 more)

### Community 1 - "Life API Services"
Cohesion: 0.06
Nodes (112): activate_destination(), add_grocery_item(), add_recurring_grocery_item(), archive_grocery_list(), complete_workout(), create_food(), create_goal(), create_grocery_list() (+104 more)

### Community 2 - "Islamic API Client"
Cohesion: 0.06
Nodes (22): IslamicAPIClient, Any, AsyncClient, QuranSessionModel, IslamicRouter, Any, AyahValue, IslamicInputError (+14 more)

### Community 3 - "Finance Bot Runtime"
Cohesion: 0.07
Nodes (43): FinanceBot, _divide(), help_text(), history_text(), idr(), date, rollover_markup(), _status() (+35 more)

### Community 4 - "Database Infrastructure"
Cohesion: 0.05
Nodes (41): Base, Database, AsyncSession, TimestampMixin, IslamicScopeModel, PrayerScheduleModel, QuranDailyStatModel, QuranProgressModel (+33 more)

### Community 5 - "Telegram Client Infrastructure"
Cohesion: 0.06
Nodes (39): build_shared_http_client(), InputFile, Any, AsyncClient, BaseModel, SecretStr, SentMessage, TelegramBotClient (+31 more)

### Community 6 - "HTTP Health Webhooks"
Cohesion: 0.05
Nodes (45): health(), get, JSONResponse, Request, JSONResponse, post, Request, _raise_body_too_large() (+37 more)

### Community 7 - "Life Domain Services"
Cohesion: 0.09
Nodes (6): LifeService, date, Exception, LifeValidationError, Decimal, ZoneInfo

### Community 8 - "Life Persistence"
Cohesion: 0.08
Nodes (7): LifeNotificationDestinationModel, LifeRepository, AsyncSession, datetime, TelegramBotModel, Record webhook evidence using the internal ``telegram_chats.id`` FK.…, TelegramChatModel

### Community 9 - "Deployment Documentation"
Cohesion: 0.06
Nodes (51): Backend Dockerfile, Backend Docker Assets, Workspace Compose Definition, Opaque Application Sessions, Automatic Bot Module Discovery, Base Bot Interface, Immutable Bot Context, Per-Bot User Membership (+43 more)

### Community 10 - "Admin API"
Cohesion: 0.12
Nodes (26): Admin, ArgumentParser, create_bot(), list_bots(), list_modules(), get, post, Request (+18 more)

### Community 11 - "Frontend Dependencies"
Cohesion: 0.06
Nodes (35): dependencies, react, react-dom, react-router-dom, @tanstack/react-query, devDependencies, tailwindcss, @tailwindcss/vite (+27 more)

### Community 12 - "Module Discovery Registry"
Cohesion: 0.12
Nodes (19): ABC, discover_modules(), _register_module(), BaseBot, BotDependencies, BotModuleRegistry, Start optional module-owned background work., Stop optional module-owned background work. (+11 more)

### Community 13 - "Authentication API"
Cohesion: 0.11
Nodes (24): authenticateTelegram(), getCurrentUser(), LaunchingBot, SessionBootstrap, TelegramAuthInput, TelegramAuthResponse, ApiError, apiRequest() (+16 more)

### Community 14 - "Application Settings"
Cohesion: 0.14
Nodes (17): field_validator, model_validator, Settings, RuntimeBot, Database, IssuedSession, PlatformAuthService, Database (+9 more)

### Community 15 - "GitLab API Client"
Cohesion: 0.14
Nodes (5): GitlabApiClient, Response, GitlabApiError, GitlabMergeRequestValue, Exception

### Community 16 - "Life Frontend Shell"
Cohesion: 0.14
Nodes (18): CurrentUser, logout(), lifeApi, Icon(), IconName, IconProps, LifeShell(), LifeShellProps (+10 more)

### Community 17 - "Reminder Executor"
Cohesion: 0.15
Nodes (18): GoalRecommendationAction, LifeReminderExecutor, SentMessage, Database-backed reminder executor independent from FastAPI request handling., ReminderDeliveryClaim, BotAlreadyExistsError, DatabaseUnavailableError, DuplicateUpdateError (+10 more)

### Community 18 - "Application Lifespan"
Cohesion: 0.16
Nodes (20): require_admin(), get_settings(), ApplicationContainer, _connect_database(), lifespan(), Database, FastAPI, _verify_and_sync_bot() (+12 more)

### Community 19 - "User Authentication"
Cohesion: 0.21
Nodes (21): authenticate_telegram_mini_app(), get_current_user(), logout(), Authenticated, get, post, Request, Response (+13 more)

### Community 20 - "Life Data Models"
Cohesion: 0.27
Nodes (19): LifeDestinationCandidateModel, LifeFoodModel, LifeGoalPreferenceModel, LifeGroceryItemModel, LifeGroceryListModel, LifeMealLogItemModel, LifeMealLogModel, LifeMealTemplateItemModel (+11 more)

### Community 21 - "TypeScript App Config"
Cohesion: 0.09
Nodes (22): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+14 more)

### Community 22 - "GitLab Design Concepts"
Cohesion: 0.13
Nodes (22): Life Reminder Executor, Immutable GitLab Audit Events, Credential Cipher Reuse, Typed GitLab API Client, GitLab Approval API, GitLab Authority at Action Time, Opaque GitLab Callback Actions, GitLab Event Executor (+14 more)

### Community 23 - "GitLab Bot Router"
Cohesion: 0.30
Nodes (5): _command(), GitlabOpsRouter, Any, TelegramUpdate, UserContext

### Community 24 - "GitLab Client Schemas"
Cohesion: 0.21
Nodes (14): normalize_gitlab_url(), AsyncClient, CallbackActionValue, GitlabBranchValue, GitlabPipelineValue, GitlabProjectValue, GitlabUserValue, ManualScriptJobValue (+6 more)

### Community 25 - "Life Frontend API Types"
Cohesion: 0.11
Nodes (18): DestinationCandidate, Food, GoalDirection, GoalPreference, GoalPreferenceInput, GoalRecommendation, GoalRecommendationDeliveryStatus, GoalRecommendationStatus (+10 more)

### Community 26 - "GitLab Bot"
Cohesion: 0.13
Nodes (10): GitlabOpsBot, TelegramBotClient, TelegramUpdate, UserContext, _factory(), BotRuntimeConfig, register(), TelegramBotClient (+2 more)

### Community 27 - "Reminder Persistence"
Cohesion: 0.29
Nodes (3): LifeReminderModel, AsyncSession, ReminderInput

### Community 28 - "Frontend App Router"
Cohesion: 0.19
Nodes (11): App(), QueryProvider(), QueryProviderProps, router, AppRoute(), LaunchRoute(), RootRoute(), PlannerPage() (+3 more)

### Community 29 - "Grocery Frontend"
Cohesion: 0.15
Nodes (10): CreateGroceryListInput, GroceryCadence, GroceryItem, GroceryList, cadenceLabel(), formatDateRange(), GroceryPage(), idr (+2 more)

### Community 30 - "TypeScript Node Config"
Cohesion: 0.12
Nodes (15): compilerOptions, allowImportingTsExtensions, lib, module, moduleDetection, moduleResolution, noEmit, skipLibCheck (+7 more)

### Community 31 - "Life Bot"
Cohesion: 0.18
Nodes (6): LifeBot, BotContext, SentMessage, TelegramUpdate, UserContext, Life Telegram adapter: entry, candidate observation, and quick actions.

### Community 32 - "Session Persistence"
Cohesion: 0.25
Nodes (8): ApplicationSessionModel, Base, TimestampMixin, ApplicationSessionRepository, AsyncSession, datetime, TelegramBotModel, TelegramUserModel

### Community 33 - "Life User Guide"
Cohesion: 0.18
Nodes (14): Panduan Penggunaan Life Bot, Calorie Target, Grocery Lists, Group Notification Privacy, Life Bot, Life Mini App, Reminder Owner Action Authorization, Planner Reminders (+6 more)

### Community 34 - "Planner Frontend"
Cohesion: 0.18
Nodes (12): RecurrenceRule, Reminder, ReminderInput, LifeSelect(), Toggle(), publicError(), ReminderForm(), ReminderRow() (+4 more)

### Community 36 - "Goal Recommendations"
Cohesion: 0.24
Nodes (4): LifeGoalRecommendationModel, datetime, RecurrenceRule, time

### Community 37 - "Bot Persistence"
Cohesion: 0.44
Nodes (3): TelegramBotModel, BotRepository, AsyncSession

### Community 38 - "Manual Script Runner Plan"
Cohesion: 0.25
Nodes (11): GitLab Ops Manual Script Runner Plan, API-Only Pipeline Creation, Approve and Run Flow, Explicit Job Name Selection, Job Hook Status Updates, No Arbitrary Shell Commands, Protected Branch Second Confirmation, Push Notifications Without Automatic Execution (+3 more)

### Community 39 - "Settings Frontend"
Cohesion: 0.35
Nodes (9): formatDate(), formatDateOnly(), formatTrend(), goalDirectionLabel(), GoalRecommendationHistory(), publicError(), recommendationStatusLabel(), recommendationStatusTone() (+1 more)

### Community 40 - "GitLab Webhook API"
Cohesion: 0.36
Nodes (8): _bad_length(), post, Request, _read_limited_body(), receive_gitlab_webhook(), _runtime(), _too_large(), JSONResponse

### Community 41 - "Project Selector Plan"
Cohesion: 0.28
Nodes (9): Business-Labeled Promotion Rules, GitLab Ops Project Selector Plan, Business-Labeled Promotion Rule, Legacy Command Parser Compatibility, Opaque Server-Side Callback Action, Selector Pagination, Permission-Filtered Project Selector, Selector-First Operational UX (+1 more)

### Community 42 - "CI Job Mapping"
Cohesion: 0.25
Nodes (9): Branch to GitLab Manual Job Mapping, CI Lint Effective Configuration, Configured Manual GitLab Job, API-Only Pipeline Source Filter, Development Environment, Manual Operation Guardrail, Production Environment, Development Operation Job (+1 more)

### Community 43 - "GitLab Ops Runbook"
Cohesion: 0.29
Nodes (8): One-Time Expiring Callback Actions, Effective CI Configuration, GitLab Job Hooks, GitLab Ops Bot Runbook, Manual Script Runner, Private PAT Onboarding, Single-Process Webhook Executor, GitLab CI Pipeline

### Community 44 - "Repository Guidelines"
Cohesion: 0.29
Nodes (7): Assistant Mode, Backend Module Structure, Graphify Maintenance, Implementor Mode, Repository Guidelines, Security and Configuration Policy, Manual Verification Responsibility

### Community 46 - "Islamic Migration"
Cohesion: 0.60
Nodes (3): timestamps(), upgrade(), Column

### Community 47 - "Update Handler"
Cohesion: 0.50
Nodes (3): BotContext, TelegramUpdate, Handle one already-authenticated, idempotently claimed update.

### Community 49 - "Frontend HTML Entry"
Cohesion: 0.50
Nodes (4): Main TSX Entrypoint, Frontend Root Mount, Telegram Platform HTML Entry Point, Telegram Web App JavaScript

## Knowledge Gaps
- **139 isolated node(s):** `telegram-bot-platform`, `name`, `private`, `version`, `type` (+134 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **73 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Application Settings` to `GitLab Formatting`, `Life API Services`, `Bot Registry`, `Database Infrastructure`, `Telegram Client Infrastructure`, `HTTP Health Webhooks`, `Life Domain Services`, `Admin API`, `Module Discovery Registry`, `Reminder Executor`, `Application Lifespan`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Why does `LifeService` connect `Life Domain Services` to `User Context`, `Life API Services`, `Goal Recommendations`, `Module Discovery Registry`, `Food Templates`, `Application Settings`, `Goal Preferences`, `Reminder Executor`, `Reminder Persistence`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `TelegramBotClient` connect `Telegram Client Infrastructure` to `Reminder Executor`, `Islamic API Client`, `Finance Bot Runtime`, `Application Settings`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `LifeService` (e.g. with `Settings` and `LifeForbiddenError`) actually correct?**
  _`LifeService` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `GitlabOpsService` (e.g. with `GitlabOpsBot` and `GitlabOpsRouter`) actually correct?**
  _`GitlabOpsService` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `GitlabOpsRepository` (e.g. with `GitlabAuditEventModel` and `GitlabCallbackActionModel`) actually correct?**
  _`GitlabOpsRepository` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `Settings` (e.g. with `Base` and `Database`) actually correct?**
  _`Settings` has 30 INFERRED edges - model-reasoned connections that need verification._