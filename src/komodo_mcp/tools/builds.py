from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from komodo_mcp.client import KomodoClient, KomodoDep

_OID = "MongoDB ObjectId from `_id.$oid`"


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def list_builds(komodo: KomodoClient = KomodoDep) -> Any:
        """List all builds in Komodo."""
        return await komodo.read("ListBuilds")

    @mcp.tool
    async def get_build(
        build: Annotated[
            str,
            Field(
                description="Build name or id. Response includes `_id.$oid` — use it as `id` for update_build/delete_build."
            ),
        ],
        komodo: KomodoClient = KomodoDep,
    ) -> Any:
        """Get detailed info about a build."""
        return await komodo.read("GetBuild", {"build": build})

    @mcp.tool
    async def create_build(
        name: str,
        config: dict[str, Any] | None = None,
        komodo: KomodoClient = KomodoDep,
    ) -> Any:
        """Create a new build configuration."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateBuild", params)

    @mcp.tool
    async def update_build(
        id: Annotated[str, Field(description=_OID)],
        config: Annotated[
            dict[str, Any],
            Field(
                description="Build config fields to update. Merged into existing config, not replaced."
            ),
        ],
        komodo: KomodoClient = KomodoDep,
    ) -> Any:
        """Update build configuration."""
        return await komodo.write("UpdateBuild", {"id": id, "config": config})

    @mcp.tool
    async def delete_build(
        id: Annotated[str, Field(description=_OID)],
        komodo: KomodoClient = KomodoDep,
    ) -> Any:
        """Delete a build."""
        return await komodo.write("DeleteBuild", {"id": id})

    @mcp.tool
    async def run_build(build: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Run a build (clone repo, build Docker image, push to registry)."""
        return await komodo.execute("RunBuild", {"build": build})
