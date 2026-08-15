.PHONY: install run migrate revision downgrade docker-up docker-dev docker-down docker-logs docker-dev-logs

ROOT_ENV := ../.env

define with_root_env
set -a; . $(ROOT_ENV); set +a; $(1)
endef

install:
	uv sync --locked

run:
	@$(call with_root_env,uv run uvicorn app.main:app --host "$${APP_HOST:-0.0.0.0}" --port "$${APP_PORT:-8000}" --reload)

migrate:
	@$(call with_root_env,uv run alembic upgrade head)

revision:
	@test -n "$(MESSAGE)" || (echo "Usage: make revision MESSAGE='description'" && exit 1)
	@$(call with_root_env,uv run alembic revision --autogenerate -m "$(MESSAGE)")

downgrade:
	@$(call with_root_env,uv run alembic downgrade -1)

docker-up:
	docker compose -f ../docker-compose.yml --profile prod up --build

docker-dev:
	docker compose -f ../docker-compose.yml --profile dev up --no-build --force-recreate

docker-down:
	docker compose -f ../docker-compose.yml down

docker-logs:
	docker compose -f ../docker-compose.yml logs -f app

docker-dev-logs:
	docker compose -f ../docker-compose.yml logs -f app-dev cloudflared
