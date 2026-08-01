.PHONY: install run migrate revision downgrade docker-up docker-dev docker-down docker-logs docker-dev-logs

install:
	uv sync --locked

run:
	uv run uvicorn app.main:app --host "$${APP_HOST:-0.0.0.0}" --port "$${APP_PORT:-8000}" --reload

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(MESSAGE)" || (echo "Usage: make revision MESSAGE='description'" && exit 1)
	uv run alembic revision --autogenerate -m "$(MESSAGE)"

downgrade:
	uv run alembic downgrade -1

docker-up:
	docker compose --profile prod up --build

docker-dev:
	docker compose --profile dev up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f app

docker-dev-logs:
	docker compose logs -f app-dev cloudflared
