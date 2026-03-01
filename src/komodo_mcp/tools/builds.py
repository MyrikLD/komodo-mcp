from typing import Any

from mcp.server.fastmcp import FastMCP

from komodo_mcp.client import komodo


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_builds() -> Any:
        """List all builds in Komodo."""
        return await komodo.read("ListBuilds")

    @mcp.tool()
    async def get_build(build: str) -> Any:
        """Get detailed info about a build by id or name."""
        return await komodo.read("GetBuild", {"build": build})

    @mcp.tool()
    async def create_build(name: str, config: dict[str, Any] | None = None) -> Any:
        """Create a new build configuration."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateBuild", params)

    @mcp.tool()
    async def update_build(id: str, config: dict[str, Any]) -> Any:
        """Update build configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateBuild", {"id": id, "config": config})

    @mcp.tool()
    async def delete_build(id: str) -> Any:
        """Delete a build by id or name."""
        return await komodo.write("DeleteBuild", {"id": id})

    @mcp.tool()
    async def run_build(build: str) -> Any:
        """Run a build (clone repo, build Docker image, push to registry)."""
        return await komodo.execute("RunBuild", {"build": build})
