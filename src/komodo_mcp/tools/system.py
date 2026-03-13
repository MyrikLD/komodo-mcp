from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from komodo_mcp.client import KomodoClient, KomodoDep

_OID = "MongoDB ObjectId from `_id.$oid`"

mcp = FastMCP()


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_version(komodo: KomodoClient = KomodoDep) -> Any:
    """Get the Komodo Core API version."""
    return await komodo.read("GetVersion")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_system_info(server: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Get system information (OS, CPU, memory, disks) for a server."""
    return await komodo.read("GetSystemInformation", {"server": server})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def list_updates(komodo: KomodoClient = KomodoDep) -> Any:
    """List recent updates/actions in Komodo."""
    return await komodo.read("ListUpdates")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def list_alerters(komodo: KomodoClient = KomodoDep) -> Any:
    """List all alerters in Komodo."""
    return await komodo.read("ListAlerters")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_alerter(
    alerter: Annotated[
        str,
        Field(
            description="Alerter name or id. Response includes `_id.$oid` — use it as `id` for update_alerter/delete_alerter."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Get detailed info about an alerter."""
    return await komodo.read("GetAlerter", {"alerter": alerter})


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
async def create_alerter(
    name: str,
    config: dict[str, Any] | None = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Create a new alerter."""
    params: dict[str, Any] = {"name": name}
    if config:
        params["config"] = config
    return await komodo.write("CreateAlerter", params)


@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def update_alerter(
    id: Annotated[str, Field(description=_OID)],
    config: Annotated[
        dict[str, Any],
        Field(
            description="Alerter config fields to update. Merged into existing config, not replaced."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Update alerter configuration."""
    return await komodo.write("UpdateAlerter", {"id": id, "config": config})


@mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
async def delete_alerter(
    id: Annotated[str, Field(description=_OID)],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Delete an alerter."""
    return await komodo.write("DeleteAlerter", {"id": id})
