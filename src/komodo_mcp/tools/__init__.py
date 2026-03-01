from fastmcp import FastMCP

from komodo_mcp.tools import (
    builds,
    deployments,
    procedures,
    repos,
    servers,
    stacks,
    system,
)


def register_all(mcp: FastMCP) -> None:
    servers.register(mcp)
    stacks.register(mcp)
    deployments.register(mcp)
    builds.register(mcp)
    repos.register(mcp)
    procedures.register(mcp)
    system.register(mcp)
