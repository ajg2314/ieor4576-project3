FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./backend/

EXPOSE 8080

CMD uv run uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
