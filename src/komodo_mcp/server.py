from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP

from komodo_mcp.config import settings
from komodo_mcp.tools import register_all

mcp = FastMCP(
    name="komodo-mcp",
    instructions="MCP server for managing Komodo DevOps platform. "
    "Provides tools for servers, stacks, deployments, builds, repos, procedures, and system management.",
)

register_all(mcp)

mcp_app = mcp.http_app(path="/", stateless_http=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(lifespan=lifespan)
app.mount("/mcp", mcp_app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
