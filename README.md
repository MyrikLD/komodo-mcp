# Komodo MCP Server

A Python MCP (Model Context Protocol) server for the [Komodo](https://komo.do) DevOps platform. Manage your servers, containers, stacks, builds, and more — directly from AI assistants like Claude.

Built with [FastMCP](https://github.com/jlowin/fastmcp), FastAPI, and httpx.

## Quick Start (Docker Compose)

1. **Create `docker-compose.yml`**:

```yaml
services:
  komodo-mcp:
    image: ghcr.io/myrikld/komodo-mcp:latest
    ports:
      - "8000:8000"
    environment:
      - KOMODO_MCP_KOMODO_URL=https://your-komodo-instance.example.com
      - KOMODO_MCP_KOMODO_API_KEY=your_api_key
      - KOMODO_MCP_KOMODO_API_SECRET=your_api_secret
      # - KOMODO_MCP_AUTH_TOKEN=your-secret-token
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

2. **Start**:

```bash
docker compose up -d
```

3. **Verify**:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Connect to MCP Client

The server exposes a Streamable HTTP endpoint at `/mcp/`.

**Claude Code** (CLI):

```bash
claude mcp add -s user --transport http komodo http://localhost:8000/mcp/
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "komodo": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

## Authentication

Set `KOMODO_MCP_AUTH_TOKEN` to require a Bearer token for all `/mcp/` requests. When set, clients must include the `Authorization: Bearer <token>` header. The `/health` endpoint remains open.

When omitted, the server works without authentication (backward-compatible).

## Configuration

All settings are configured via environment variables with the `KOMODO_MCP_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `KOMODO_MCP_KOMODO_URL` | Komodo instance URL | *required* |
| `KOMODO_MCP_KOMODO_API_KEY` | API key | *required* |
| `KOMODO_MCP_KOMODO_API_SECRET` | API secret | *required* |
| `KOMODO_MCP_HOST` | Server bind host | `0.0.0.0` |
| `KOMODO_MCP_PORT` | Server bind port | `8000` |
| `KOMODO_MCP_AUTH_TOKEN` | Bearer token for `/mcp/` endpoint | *disabled* |

## Local Development

```bash
# Install dependencies
uv sync

# Set environment variables
export KOMODO_MCP_KOMODO_URL=https://your-instance.example.com
export KOMODO_MCP_KOMODO_API_KEY=your_key
export KOMODO_MCP_KOMODO_API_SECRET=your_secret

# Run the server
komodo-mcp

# Run tests
uv run pytest tests/ -v

# Lint
uv run black --check src/ tests/
```

## Tech Stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP SDK with dependency injection
- **[FastAPI](https://fastapi.tiangolo.com)** — HTTP framework
- **[httpx](https://www.python-httpx.org)** — Async HTTP client
- **[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** — Configuration management
- **[uv](https://docs.astral.sh/uv/)** — Package manager

## Links

- [GitHub](https://github.com/MyrikLD/komodo-mcp)
- [Docker Image](https://github.com/MyrikLD/komodo-mcp/pkgs/container/komodo-mcp)
- [Komodo Documentation](https://docs.komo.do)
- [Komodo API Reference](https://docs.komo.do/api)
- [Model Context Protocol](https://modelcontextprotocol.io)
