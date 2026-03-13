from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from komodo_mcp.client import KomodoClient, KomodoDep

_OID = "MongoDB ObjectId from `_id.$oid`"

mcp = FastMCP()


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def list_servers(komodo: KomodoClient = KomodoDep) -> Any:
    """List all servers in Komodo."""
    return await komodo.read("ListServers")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_server(
    server: Annotated[
        str,
        Field(
            description="Server name or id. Response includes `_id.$oid` — use it as `id` for update_server/delete_server."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Get detailed info about a server."""
    return await komodo.read("GetServer", {"server": server})


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
async def create_server(
    name: str,
    config: dict[str, Any] | None = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Create a new server."""
    params: dict[str, Any] = {"name": name}
    if config:
        params["config"] = config
    return await komodo.write("CreateServer", params)


@mcp.tool(
    annotations={"destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
)
async def update_server(
    id: Annotated[str, Field(description=_OID)],
    config: Annotated[
        dict[str, Any],
        Field(
            description="Server config fields to update. Merged into existing config, not replaced."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Update server configuration."""
    return await komodo.write("UpdateServer", {"id": id, "config": config})


@mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
async def delete_server(
    id: Annotated[str, Field(description=_OID)],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Delete a server."""
    return await komodo.write("DeleteServer", {"id": id})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_server_stats(server: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Get system stats (CPU, memory, disk) for a server."""
    return await komodo.read("GetSystemStats", {"server": server})
