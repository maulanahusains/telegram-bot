# Graph Report - .  (2026-08-15)

## Corpus Check
- 90 files · ~37,409 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 725 nodes · 2223 edges · 89 communities (21 shown, 68 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 286 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Admin Bot Management
- Islamic API Client
- Finance Bot Operations
- Bot Registry Contracts
- Database Model Infrastructure
- HTTP Health Webhook
- Telegram Client Transport
- Islamic Bot Routing
- Islamic Data Persistence
- User API Schemas
- Finance Data Persistence
- Bot Data Persistence
- Product Architecture Concepts
- Compose Deployment Stack
- Islamic Migration
- Agent Operating Modes
- Application Package
- Sample Repository Package
- Sample Webhook
- Platform Package
- Shared Utilities Package
- Reminder Lifecycle
- Manual Verification Policy
- Bot Module Boundaries
- Secret Management Policy
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols
- Shared Type Symbols

## God Nodes (most connected - your core abstractions)
1. `TelegramBotClient` - 54 edges
2. `IslamicService` - 50 edges
3. `Database` - 47 edges
4. `FinanceService` - 45 edges
5. `TelegramUpdate` - 41 edges
6. `IslamicRouter` - 38 edges
7. `Settings` - 37 edges
8. `UserContext` - 35 edges
9. `FinanceInputError` - 33 edges
10. `IslamicInputError` - 31 edges

## Surprising Connections (you probably didn't know these)
- `Base` --uses--> `Settings`  [INFERRED]
  backend/app/core/database.py → backend/app/core/config.py
- `TimestampMixin` --uses--> `Settings`  [INFERRED]
  backend/app/core/database.py → backend/app/core/config.py
- `BaseBot` --uses--> `Settings`  [INFERRED]
  backend/app/core/registry.py → backend/app/core/config.py
- `BotDependencies` --uses--> `Settings`  [INFERRED]
  backend/app/core/registry.py → backend/app/core/config.py
- `BotModuleRegistry` --uses--> `Settings`  [INFERRED]
  backend/app/core/registry.py → backend/app/core/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Development Compose Stack** — docker_compose_postgres_service, docker_compose_app_dev_service, docker_compose_cloudflared_service, docker_compose_health_gated_dependencies, docker_compose_development_bind_mounts [EXTRACTED 1.00]

## Communities (89 total, 68 thin omitted)

### Community 0 - "Admin Bot Management"
Cohesion: 0.05
Nodes (60): Admin, ArgumentParser, create_bot(), list_bots(), list_modules(), get, post, Request (+52 more)

### Community 1 - "Islamic API Client"
Cohesion: 0.07
Nodes (21): AsyncSession, IslamicAPIClient, Any, AsyncClient, QuranSessionModel, AyahValue, IslamicInputError, PrayerClaim (+13 more)

### Community 2 - "Finance Bot Operations"
Cohesion: 0.09
Nodes (35): FinanceBot, _divide(), help_text(), history_text(), idr(), date, rollover_markup(), _status() (+27 more)

### Community 3 - "Bot Registry Contracts"
Cohesion: 0.07
Nodes (40): ABC, BaseBot, BotDependencies, BotModuleRegistry, BotContext, Start optional module-owned background work., Stop optional module-owned background work., Handle one already-authenticated, idempotently claimed update. (+32 more)

### Community 4 - "Database Model Infrastructure"
Cohesion: 0.08
Nodes (33): Base, TimestampMixin, SampleUserProfileModel, AsyncSession, Bot configuration domain., Telegram update idempotency domain., StrEnum, TelegramUpdateModel (+25 more)

### Community 5 - "HTTP Health Webhook"
Cohesion: 0.07
Nodes (45): health(), get, JSONResponse, Request, JSONResponse, post, Request, _raise_body_too_large() (+37 more)

### Community 6 - "Telegram Client Transport"
Cohesion: 0.14
Nodes (13): InputFile, Any, AsyncClient, BaseModel, SecretStr, SentMessage, TelegramBotClient, TelegramBotIdentity (+5 more)

### Community 7 - "Islamic Bot Routing"
Cohesion: 0.22
Nodes (4): IslamicRouter, Any, ScopeValue, TelegramCallbackQuery

### Community 8 - "Islamic Data Persistence"
Cohesion: 0.17
Nodes (8): IslamicScopeModel, PrayerScheduleModel, QuranDailyStatModel, QuranProgressModel, IslamicRepository, AsyncSession, date, datetime

### Community 9 - "User API Schemas"
Cohesion: 0.17
Nodes (9): BotUserPublic, BaseModel, TelegramUserPublic, UserStateValue, Any, datetime, UserManagementService, UserStateService (+1 more)

### Community 10 - "Finance Data Persistence"
Cohesion: 0.22
Nodes (6): FinanceBudgetPeriodModel, FinanceProfileModel, FinanceTransactionModel, FinanceRepository, AsyncSession, date

### Community 11 - "Bot Data Persistence"
Cohesion: 0.44
Nodes (3): TelegramBotModel, BotRepository, AsyncSession

### Community 12 - "Product Architecture Concepts"
Cohesion: 0.25
Nodes (8): FastAPI Modular Monolith, Runtime Bot Registry, Update Idempotency and Leases, Telegram initData Authentication, Life Modular-Monolith Module, Life MVP, Backend Relocation Plan, Telegram Bot Workspace

### Community 13 - "Compose Deployment Stack"
Cohesion: 0.38
Nodes (7): Development Application Service, Production Application Service, Cloudflare Tunnel Service, Development Bind Mounts, Health-Gated Service Dependencies, Migration Before Application Startup, PostgreSQL Compose Service

### Community 14 - "Islamic Migration"
Cohesion: 0.60
Nodes (3): timestamps(), upgrade(), Column

## Knowledge Gaps
- **10 isolated node(s):** `telegram-bot-platform`, `Cloudflare Tunnel Service`, `Development Bind Mounts`, `Telegram Bot Workspace`, `Update Idempotency and Leases` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **68 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Admin Bot Management` to `Islamic API Client`, `Finance Bot Operations`, `Bot Registry Contracts`, `Database Model Infrastructure`, `Islamic Data Persistence`, `User API Schemas`, `Finance Data Persistence`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `TelegramBotClient` connect `Telegram Client Transport` to `Admin Bot Management`, `Islamic API Client`, `Finance Bot Operations`, `Bot Registry Contracts`, `Islamic Bot Routing`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `TelegramUpdate` connect `Bot Registry Contracts` to `Admin Bot Management`, `Islamic API Client`, `Finance Bot Operations`, `Database Model Infrastructure`, `HTTP Health Webhook`, `Islamic Bot Routing`, `User API Schemas`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 13 inferred relationships involving `TelegramBotClient` (e.g. with `ApplicationContainer` and `BaseBot`) actually correct?**
  _`TelegramBotClient` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `IslamicService` (e.g. with `Database` and `IslamicAPIClient`) actually correct?**
  _`IslamicService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `Database` (e.g. with `Settings` and `ApplicationContainer`) actually correct?**
  _`Database` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `FinanceService` (e.g. with `FinanceRouter` and `Database`) actually correct?**
  _`FinanceService` has 14 INFERRED edges - model-reasoned connections that need verification._