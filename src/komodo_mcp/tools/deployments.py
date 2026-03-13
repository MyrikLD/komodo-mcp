from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from komodo_mcp.client import KomodoClient, KomodoDep

_OID = "MongoDB ObjectId from `_id.$oid`"

mcp = FastMCP()


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def list_deployments(komodo: KomodoClient = KomodoDep) -> Any:
    """List all deployments in Komodo."""
    return await komodo.read("ListDeployments")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_deployment(
    deployment: Annotated[
        str,
        Field(
            description="Deployment name or id. Response includes `_id.$oid` — use it as `id` for update_deployment/delete_deployment."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Get detailed info about a deployment."""
    return await komodo.read("GetDeployment", {"deployment": deployment})


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_deployment_log(deployment: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Get logs for a deployment container."""
    return await komodo.read("GetDeploymentLog", {"deployment": deployment})


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
async def create_deployment(
    name: str,
    config: dict[str, Any] | None = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Create a new deployment."""
    params: dict[str, Any] = {"name": name}
    if config:
        params["config"] = config
    return await komodo.write("CreateDeployment", params)


@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def update_deployment(
    id: Annotated[str, Field(description=_OID)],
    config: Annotated[
        dict[str, Any],
        Field(
            description="Deployment config fields to update. Merged into existing config, not replaced."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Update deployment configuration."""
    return await komodo.write("UpdateDeployment", {"id": id, "config": config})


@mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
async def delete_deployment(
    id: Annotated[str, Field(description=_OID)],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Delete a deployment."""
    return await komodo.write("DeleteDeployment", {"id": id})


@mcp.tool(annotations={"destructiveHint": True})
async def deploy(
    deployment: str,
    stop_signal: Annotated[
        str | None,
        Field(
            description="Signal sent to the container before stopping (e.g. SIGTERM, SIGINT)."
        ),
    ] = None,
    stop_time: Annotated[
        int | None,
        Field(
            description="Seconds to wait for graceful stop before forcing. Defaults to Docker's timeout."
        ),
    ] = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Deploy a deployment (pull image and recreate container)."""
    params: dict[str, Any] = {"deployment": deployment}
    if stop_signal:
        params["stop_signal"] = stop_signal
    if stop_time is not None:
        params["stop_time"] = stop_time
    return await komodo.execute("Deploy", params)


@mcp.tool(annotations={"destructiveHint": False, "idempotentHint": True})
async def start_deployment(deployment: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Start a stopped deployment container."""
    return await komodo.execute("StartDeployment", {"deployment": deployment})


@mcp.tool(annotations={"destructiveHint": True, "idempotentHint": True})
async def stop_deployment(
    deployment: str,
    stop_time: Annotated[
        int | None,
        Field(
            description="Seconds to wait for graceful stop before forcing. Defaults to Docker's timeout."
        ),
    ] = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Stop a deployment container."""
    params: dict[str, Any] = {"deployment": deployment}
    if stop_time is not None:
        params["stop_time"] = stop_time
    return await komodo.execute("StopDeployment", params)


@mcp.tool(annotations={"destructiveHint": True})
async def restart_deployment(deployment: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Restart a deployment container."""
    return await komodo.execute("RestartDeployment", {"deployment": deployment})
