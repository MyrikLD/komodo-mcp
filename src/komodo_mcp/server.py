import uvicorn
from fastmcp import FastMCP

from komodo_mcp.auth import BearerTokenMiddleware
from komodo_mcp.config import settings
from komodo_mcp.tools import builds, deployments, procedures, repos, servers, stacks, system

mcp = FastMCP(
    name="komodo-mcp",
    instructions="MCP server for managing Komodo DevOps platform. "
    "Provides tools for servers, stacks, deployments, builds, repos, procedures, and system management.",
)

mcp.mount(servers)
mcp.mount(stacks)
mcp.mount(deployments)
mcp.mount(builds)
mcp.mount(repos)
mcp.mount(procedures)
mcp.mount(system)

app = mcp.http_app(path="/", stateless_http=True)

if settings.AUTH_TOKEN:
    app.add_middleware(BearerTokenMiddleware, token=settings.AUTH_TOKEN)


def main() -> None:
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
