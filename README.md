# Komodo MCP Server

A Python MCP (Model Context Protocol) server for the [Komodo](https://komo.do) DevOps platform. Manage your servers, containers, stacks, builds, and more — directly from AI assistants like Claude.

Built with [FastMCP](https://github.com/PrefectHQ/fastmcp), uvicorn, and httpx.

## Quick Start (Docker Compose)

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
    restart: unless-stopped
```

```bash
docker compose up -d
```

## Connect to MCP Client

The server exposes a Streamable HTTP endpoint at `/`.

**Claude Code** (CLI):

```bash
claude mcp add -s user --transport http komodo http://localhost:8000/
```

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "komodo": {
      "type": "http",
      "url": "http://localhost:8000/"
    }
  }
}
```

## Authentication

The server supports OAuth 2.1 with a browser-based login page. When OAuth is enabled, MCP clients are redirected to a login form before receiving an access token.

### Enabling OAuth

Set all three variables:

```bash
KOMODO_MCP_OAUTH_JWT_SECRET=<random string, 32+ chars>
KOMODO_MCP_OAUTH_PASSWORD=<password shown in browser login form>
KOMODO_MCP_BASE_URL=https://mcp.example.com   # public URL of this server
```

When OAuth is active, the server exposes standard OAuth 2.1 endpoints:

| Endpoint | Description |
|----------|-------------|
| `/.well-known/oauth-authorization-server` | OAuth metadata discovery |
| `/register` | Dynamic Client Registration (RFC 7591) |
| `/authorize` | Authorization endpoint — redirects to `/login` |
| `/login` | Password login page (browser) |
| `/token` | Token endpoint |
| `/revoke` | Token revocation |

**Flow**: MCP client → `/authorize` → browser opens `/login` → user enters password → client receives JWT access token (1h) + refresh token (30d).

Without OAuth configured, the server accepts all connections without authentication.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `KOMODO_MCP_KOMODO_URL` | Komodo instance URL | *required* |
| `KOMODO_MCP_KOMODO_API_KEY` | API key | *required* |
| `KOMODO_MCP_KOMODO_API_SECRET` | API secret | *required* |
| `KOMODO_MCP_HOST` | Server bind host | `0.0.0.0` |
| `KOMODO_MCP_PORT` | Server bind port | `8000` |
| `KOMODO_MCP_OAUTH_JWT_SECRET` | Secret for signing JWT tokens | *OAuth disabled* |
| `KOMODO_MCP_OAUTH_PASSWORD` | Password for the browser login page | *OAuth disabled* |
| `KOMODO_MCP_BASE_URL` | Public URL of this server (used in OAuth metadata) | *OAuth disabled* |

## Local Development

```bash
uv sync

export KOMODO_MCP_KOMODO_URL=https://your-instance.example.com
export KOMODO_MCP_KOMODO_API_KEY=your_key
export KOMODO_MCP_KOMODO_API_SECRET=your_secret

komodo-mcp

# tests
python -m pytest tests/
```

## Tech Stack

- **[FastMCP](https://github.com/PrefectHQ/fastmcp)** — MCP framework with OAuth 2.1 support
- **[uvicorn](https://www.uvicorn.org)** — ASGI server
- **[httpx](https://www.python-httpx.org)** — Async HTTP client for Komodo API
- **[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** — Configuration

## Links

- [GitHub](https://github.com/MyrikLD/komodo-mcp)
- [Docker Image](https://github.com/MyrikLD/komodo-mcp/pkgs/container/komodo-mcp)
- [Komodo Documentation](https://docs.komo.do)
- [Model Context Protocol](https://modelcontextprotocol.io)
