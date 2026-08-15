FROM ghcr.io/astral-sh/uv:0.8.14 AS uv

FROM python:3.13-slim-bookworm AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project --no-dev
COPY app ./app
RUN uv sync --locked --no-dev

FROM python:3.13-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
    && apt-get install --no-install-recommends --yes tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app
WORKDIR /app
COPY --from=builder --chown=app:app /build/.venv ./.venv
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini pyproject.toml ./
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
