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

## Tools (53)

### Servers

| Tool | Description |
|------|-------------|
| `list_servers` | List all servers |
| `get_server` | Get server details |
| `create_server` | Create a new server |
| `update_server` | Update server configuration |
| `delete_server` | Delete a server |
| `get_server_stats` | Get server resource stats (CPU, RAM, disk) |

### Stacks

| Tool | Description |
|------|-------------|
| `list_stacks` | List all stacks |
| `get_stack` | Get stack details |
| `get_stack_log` | Get stack logs |
| `create_stack` | Create a new stack |
| `update_stack` | Update stack configuration |
| `delete_stack` | Delete a stack |
| `deploy_stack` | Deploy a stack |
| `start_stack` | Start a stopped stack |
| `stop_stack` | Stop a running stack |
| `restart_stack` | Restart a stack |

### Deployments

| Tool | Description |
|------|-------------|
| `list_deployments` | List all deployments |
| `get_deployment` | Get deployment details |
| `get_deployment_log` | Get deployment logs |
| `create_deployment` | Create a new deployment |
| `update_deployment` | Update deployment configuration |
| `delete_deployment` | Delete a deployment |
| `deploy` | Deploy a deployment |
| `start_deployment` | Start a stopped deployment |
| `stop_deployment` | Stop a running deployment |
| `restart_deployment` | Restart a deployment |

### Builds

| Tool | Description |
|------|-------------|
| `list_builds` | List all builds |
| `get_build` | Get build details |
| `create_build` | Create a new build |
| `update_build` | Update build configuration |
| `delete_build` | Delete a build |
| `run_build` | Run a build |

### Repos

| Tool | Description |
|------|-------------|
| `list_repos` | List all repos |
| `get_repo` | Get repo details |
| `create_repo` | Create a new repo |
| `update_repo` | Update repo configuration |
| `delete_repo` | Delete a repo |
| `clone_repo` | Clone a repo |
| `pull_repo` | Pull latest changes |

### Procedures

| Tool | Description |
|------|-------------|
| `list_procedures` | List all procedures |
| `get_procedure` | Get procedure details |
| `create_procedure` | Create a new procedure |
| `update_procedure` | Update procedure configuration |
| `delete_procedure` | Delete a procedure |
| `run_procedure` | Run a procedure |

### System

| Tool | Description |
|------|-------------|
| `get_version` | Get Komodo version |
| `get_system_info` | Get server system information |
| `list_updates` | List available updates |
| `list_alerters` | List all alerters |
| `get_alerter` | Get alerter details |
| `create_alerter` | Create a new alerter |
| `update_alerter` | Update alerter configuration |
| `delete_alerter` | Delete an alerter |

## Configuration

All settings are configured via environment variables with the `KOMODO_MCP_` prefix:

| Variable | Description | Default |
|----------|-------------|---------|
| `KOMODO_MCP_KOMODO_URL` | Komodo instance URL | *required* |
| `KOMODO_MCP_KOMODO_API_KEY` | API key | *required* |
| `KOMODO_MCP_KOMODO_API_SECRET` | API secret | *required* |
| `KOMODO_MCP_HOST` | Server bind host | `0.0.0.0` |
| `KOMODO_MCP_PORT` | Server bind port | `8000` |

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
