from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from komodo_mcp.client import komodo
from komodo_mcp.config import settings
from komodo_mcp.tools import register_all

mcp = FastMCP(
    name="komodo-mcp",
    instructions="MCP server for managing Komodo DevOps platform. "
    "Provides tools for servers, stacks, deployments, builds, repos, procedures, and system management.",
    stateless_http=True,
)

register_all(mcp)

# Build the streamable HTTP app to initialize session_manager
_mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with komodo.lifespan(), mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)
app.mount("/mcp", _mcp_app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
