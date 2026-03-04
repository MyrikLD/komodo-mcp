from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from komodo_mcp.client import KomodoClient, KomodoDep

_OID = "MongoDB ObjectId from `_id.$oid`"
_SERVICES = "Specific service names to target. Omit to affect all services."
_STOP_TIME = (
    "Seconds to wait for graceful stop before forcing. Defaults to Docker's timeout."
)

mcp = FastMCP()


@mcp.tool
async def list_stacks(komodo: KomodoClient = KomodoDep) -> Any:
    """List all stacks in Komodo."""
    return await komodo.read("ListStacks")


@mcp.tool
async def get_stack(
    stack: Annotated[
        str,
        Field(
            description="Stack name or id. Response includes `_id.$oid` — use it as `id` for update_stack/delete_stack."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Get detailed info about a stack."""
    return await komodo.read("GetStack", {"stack": stack})


@mcp.tool
async def get_stack_log(stack: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Get logs for a stack (all services combined, no per-service filtering)."""
    return await komodo.read("GetStackLog", {"stack": stack})


@mcp.tool
async def create_stack(
    name: str,
    config: dict[str, Any] | None = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Create a new stack."""
    params: dict[str, Any] = {"name": name}
    if config:
        params["config"] = config
    return await komodo.write("CreateStack", params)


@mcp.tool
async def update_stack(
    id: Annotated[str, Field(description=_OID)],
    config: Annotated[
        dict[str, Any],
        Field(
            description=(
                "Stack config fields to update. Merged into existing config, not replaced. "
                "Common fields: `file_contents` (compose.yaml as string), "
                "`environment` (newline-separated KEY=VALUE pairs for .env), "
                "`server_id` (target server ObjectId), "
                "`run_directory` (working directory for compose)."
            )
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Update stack configuration."""
    return await komodo.write("UpdateStack", {"id": id, "config": config})


@mcp.tool
async def delete_stack(
    id: Annotated[str, Field(description=_OID)],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Delete a stack."""
    return await komodo.write("DeleteStack", {"id": id})


@mcp.tool
async def deploy_stack(
    stack: str,
    services: Annotated[list[str] | None, Field(description=_SERVICES)] = None,
    stop_time: Annotated[int | None, Field(description=_STOP_TIME)] = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Pull latest images and recreate containers (docker compose up --force-recreate).
    Use after updating compose config or to apply image updates."""
    params: dict[str, Any] = {"stack": stack}
    if services:
        params["services"] = services
    if stop_time is not None:
        params["stop_time"] = stop_time
    return await komodo.execute("DeployStack", params)


@mcp.tool
async def start_stack(
    stack: str,
    services: Annotated[list[str] | None, Field(description=_SERVICES)] = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Start a stopped stack without recreating containers (docker compose start)."""
    params: dict[str, Any] = {"stack": stack}
    if services:
        params["services"] = services
    return await komodo.execute("StartStack", params)


@mcp.tool
async def stop_stack(
    stack: str,
    services: Annotated[list[str] | None, Field(description=_SERVICES)] = None,
    stop_time: Annotated[int | None, Field(description=_STOP_TIME)] = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Stop a running stack without removing containers (docker compose stop)."""
    params: dict[str, Any] = {"stack": stack}
    if services:
        params["services"] = services
    if stop_time is not None:
        params["stop_time"] = stop_time
    return await komodo.execute("StopStack", params)


@mcp.tool
async def restart_stack(
    stack: str,
    services: Annotated[list[str] | None, Field(description=_SERVICES)] = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Restart running containers without pulling images or recreating them (docker compose restart).
    Use deploy_stack instead to apply config changes or pull new images."""
    params: dict[str, Any] = {"stack": stack}
    if services:
        params["services"] = services
    return await komodo.execute("RestartStack", params)
