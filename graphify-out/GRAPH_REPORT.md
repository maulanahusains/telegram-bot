# Graph Report - .  (2026-08-01)

## Corpus Check
- Corpus is ~17,174 words - fits in a single context window. You may not need a graph.

## Summary
- 528 nodes · 1656 edges · 31 communities (18 shown, 13 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 246 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Finance Bot Services
- HTTP API Routing
- Bot Runtime Registry
- Finance Persistence Domain
- Application Health Lifecycle
- Configuration and Telegram Client
- Logging and Error Middleware
- User Management Domain
- Platform Architecture Concepts
- Bot Repository Persistence
- Container Deployment Stack
- User Identity Isolation
- Agent Operating Modes
- Manual Verification Policy
- Application Package
- Bot Module Namespace
- Sample Repositories
- Sample Webhook Adapter
- Bot Configuration Domain
- Platform Domain Namespace
- Update Idempotency Domain
- User Identity Domain
- Shared Utilities Namespace
- Modular Platform Overview
- Python Project Metadata

## God Nodes (most connected - your core abstractions)
1. `TelegramBotClient` - 45 edges
2. `FinanceService` - 45 edges
3. `Database` - 43 edges
4. `Settings` - 37 edges
5. `TelegramUpdate` - 35 edges
6. `FinanceInputError` - 33 edges
7. `UserContext` - 28 edges
8. `BotModuleRegistry` - 27 edges
9. `lifespan()` - 25 edges
10. `InvalidBotModuleError` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Manual Verification Policy` --semantically_similar_to--> `Operational Verification Checklist`  [INFERRED] [semantically similar]
  AGENTS.md → README.md
- `Bot Module Boundary Policy` --semantically_similar_to--> `Bot Module Contract`  [INFERRED] [semantically similar]
  AGENTS.md → README.md
- `Secret Management Policy` --conceptually_related_to--> `Encrypted Per-Bot Credentials`  [INFERRED]
  AGENTS.md → README.md
- `Secret Management Policy` --conceptually_related_to--> `Redacted Structured Logging`  [INFERRED]
  AGENTS.md → README.md
- `Development Compose Profile` --references--> `Development Application Service`  [EXTRACTED]
  README.md → docker-compose.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Telegram Update Processing Pipeline** — readme_generic_webhook_api, readme_runtime_bot_registry, readme_update_idempotency, readme_user_context_service, readme_postgresql, readme_bot_module_contract [EXTRACTED 1.00]
- **Isolated Bot User Data Model** — readme_global_identity_and_bot_membership, readme_versioned_bot_user_state, readme_automatic_registration, readme_postgresql [EXTRACTED 1.00]
- **Development Compose Stack** — docker_compose_postgres_service, docker_compose_app_dev_service, docker_compose_cloudflared_service, docker_compose_health_gated_dependencies, docker_compose_development_bind_mounts [EXTRACTED 1.00]

## Communities (31 total, 13 thin omitted)

### Community 0 - "Finance Bot Services"
Cohesion: 0.10
Nodes (32): _divide(), help_text(), history_text(), idr(), date, rollover_markup(), _status(), summary_text() (+24 more)

### Community 1 - "HTTP API Routing"
Cohesion: 0.07
Nodes (50): Admin, create_bot(), list_bots(), list_modules(), get, post, Request, update_bot() (+42 more)

### Community 2 - "Bot Runtime Registry"
Cohesion: 0.08
Nodes (36): ABC, BaseBot, BotDependencies, BotContext, Start optional module-owned background work., Stop optional module-owned background work., Handle one already-authenticated, idempotently claimed update., FinanceBot (+28 more)

### Community 3 - "Finance Persistence Domain"
Cohesion: 0.08
Nodes (32): Base, TimestampMixin, FinanceBudgetPeriodModel, FinanceProfileModel, FinanceTransactionModel, StrEnum, RolloverStatus, FinanceRepository (+24 more)

### Community 4 - "Application Health Lifecycle"
Cohesion: 0.06
Nodes (37): require_admin(), health(), get, JSONResponse, Request, get_settings(), Database, AsyncSession (+29 more)

### Community 5 - "Configuration and Telegram Client"
Cohesion: 0.10
Nodes (19): SecretStr, Settings, build_shared_http_client(), InputFile, Any, BaseModel, SecretStr, SentMessage (+11 more)

### Community 6 - "Logging and Error Middleware"
Cohesion: 0.13
Nodes (22): configure_logging(), get_logger(), Any, redact_sensitive(), _redact_value(), _error_response(), install_exception_handlers(), FastAPI (+14 more)

### Community 7 - "User Management Domain"
Cohesion: 0.19
Nodes (9): BotUserPublic, BaseModel, TelegramUserPublic, UserStateValue, Any, datetime, UserManagementService, UserStateService (+1 more)

### Community 8 - "Platform Architecture Concepts"
Cohesion: 0.16
Nodes (15): Bot Module Boundary Policy, Secret Management Policy, Authenticated Admin API, Bot Module Contract, Degraded Health Model, Encrypted Per-Bot Credentials, Generic Webhook API, Trusted Bot Module Discovery (+7 more)

### Community 9 - "Bot Repository Persistence"
Cohesion: 0.38
Nodes (3): TelegramBotModel, BotRepository, AsyncSession

### Community 10 - "Container Deployment Stack"
Cohesion: 0.24
Nodes (11): Development Application Service, Production Application Service, Cloudflare Tunnel Service, Development Bind Mounts, Health-Gated Service Dependencies, Migration Before Application Startup, PostgreSQL Compose Service, Docker Assets Directory (+3 more)

### Community 11 - "User Identity Isolation"
Cohesion: 0.50
Nodes (5): Automatic User Registration, Finance Bot, Global Identity and Per-Bot Membership, Sample Bot, Versioned Per-Bot User State

## Knowledge Gaps
- **10 isolated node(s):** `telegram-bot-platform`, `Telegram Bot Platform`, `Injected Telegram Client`, `Docker Deployment`, `Authenticated Admin API` (+5 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Application Health Lifecycle` to `Finance Bot Services`, `HTTP API Routing`, `Bot Runtime Registry`, `Finance Persistence Domain`, `Configuration and Telegram Client`, `User Management Domain`, `Bot Repository Persistence`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `TelegramBotClient` connect `Configuration and Telegram Client` to `Finance Bot Services`, `HTTP API Routing`, `Bot Runtime Registry`, `Application Health Lifecycle`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `Settings` connect `Configuration and Telegram Client` to `HTTP API Routing`, `Bot Runtime Registry`, `Finance Persistence Domain`, `Application Health Lifecycle`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `TelegramBotClient` (e.g. with `ApplicationContainer` and `BaseBot`) actually correct?**
  _`TelegramBotClient` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `FinanceService` (e.g. with `FinanceRouter` and `Database`) actually correct?**
  _`FinanceService` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Database` (e.g. with `Settings` and `ApplicationContainer`) actually correct?**
  _`Database` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `Settings` (e.g. with `Base` and `Database`) actually correct?**
  _`Settings` has 19 INFERRED edges - model-reasoned connections that need verification._