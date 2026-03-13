from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from komodo_mcp.client import KomodoClient, KomodoDep

_OID = "MongoDB ObjectId from `_id.$oid`"

mcp = FastMCP()


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def list_repos(komodo: KomodoClient = KomodoDep) -> Any:
    """List all repositories in Komodo."""
    return await komodo.read("ListRepos")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
async def get_repo(
    repo: Annotated[
        str,
        Field(
            description="Repository name or id. Response includes `_id.$oid` — use it as `id` for update_repo/delete_repo."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Get detailed info about a repository."""
    return await komodo.read("GetRepo", {"repo": repo})


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
async def create_repo(
    name: str,
    config: dict[str, Any] | None = None,
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Create a new repository."""
    params: dict[str, Any] = {"name": name}
    if config:
        params["config"] = config
    return await komodo.write("CreateRepo", params)


@mcp.tool(
    annotations={
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def update_repo(
    id: Annotated[str, Field(description=_OID)],
    config: Annotated[
        dict[str, Any],
        Field(
            description="Repository config fields to update. Merged into existing config, not replaced."
        ),
    ],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Update repository configuration."""
    return await komodo.write("UpdateRepo", {"id": id, "config": config})


@mcp.tool(annotations={"idempotentHint": True, "openWorldHint": False})
async def delete_repo(
    id: Annotated[str, Field(description=_OID)],
    komodo: KomodoClient = KomodoDep,
) -> Any:
    """Delete a repository."""
    return await komodo.write("DeleteRepo", {"id": id})


@mcp.tool(annotations={"destructiveHint": True})
async def clone_repo(repo: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Clone a repository to its target server."""
    return await komodo.execute("CloneRepo", {"repo": repo})


@mcp.tool(annotations={"destructiveHint": False})
async def pull_repo(repo: str, komodo: KomodoClient = KomodoDep) -> Any:
    """Pull latest changes for a repository on its target server."""
    return await komodo.execute("PullRepo", {"repo": repo})
