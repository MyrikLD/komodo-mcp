FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app/.venv .venv/

ENV PATH="/app/.venv/bin:$PATH"
# Revoked-token list; mount a volume here to keep revocations across recreation
ENV KOMODO_MCP_STATE_DIR=/data
RUN mkdir -p /data

EXPOSE 8000

CMD ["komodo-mcp"]
