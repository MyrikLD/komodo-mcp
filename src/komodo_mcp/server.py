import logging

import uvicorn
from fastmcp import FastMCP

from komodo_mcp.config import settings

logger = logging.getLogger(__name__)
from komodo_mcp.oauth import KomodoOAuthProvider
from komodo_mcp.tools import (
    builds,
    deployments,
    procedures,
    repos,
    servers,
    stacks,
    system,
)


def _build_auth() -> KomodoOAuthProvider | None:
    missing = [
        name
        for name, val in [
            ("KOMODO_MCP_OAUTH_JWT_SECRET", settings.OAUTH_JWT_SECRET),
            ("KOMODO_MCP_OAUTH_PASSWORD", settings.OAUTH_PASSWORD),
            ("KOMODO_MCP_BASE_URL", settings.BASE_URL),
        ]
        if not val
    ]
    if missing:
        logger.warning("OAuth disabled — missing env vars: %s", ", ".join(missing))
        return None
    logger.info("OAuth enabled, base_url=%s", settings.BASE_URL)
    return KomodoOAuthProvider(
        base_url=settings.BASE_URL,
        jwt_secret=settings.OAUTH_JWT_SECRET,
        password=settings.OAUTH_PASSWORD,
    )


mcp = FastMCP(
    name="komodo-mcp",
    instructions="MCP server for managing Komodo DevOps platform. "
    "Provides tools for servers, stacks, deployments, builds, repos, procedures, and system management.",
    auth=_build_auth(),
)

mcp.mount(servers)
mcp.mount(stacks)
mcp.mount(deployments)
mcp.mount(builds)
mcp.mount(repos)
mcp.mount(procedures)
mcp.mount(system)

app = mcp.http_app(path="/", stateless_http=True)


def main() -> None:
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
