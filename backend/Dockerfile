# --- Stage 1: Base Setup ---
FROM python:3.11-slim AS python_base

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=0
ENV UV_LINK_MODE=copy

WORKDIR /app

# --- Stage 2: Builder ---
FROM python_base AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --link-mode=copy


# --- Stage 3: Dev Environment ---
FROM python_base AS dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --group dev --link-mode=copy

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]


# --- Stage 4: Production ---
FROM python_base AS prod

RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin -c "Application user" appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
