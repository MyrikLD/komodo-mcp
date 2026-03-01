from typing import Any

from mcp.server.fastmcp import FastMCP

from komodo_mcp.client import komodo


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_repos() -> Any:
        """List all repositories in Komodo."""
        return await komodo.read("ListRepos")

    @mcp.tool()
    async def get_repo(repo: str) -> Any:
        """Get detailed info about a repository by id or name."""
        return await komodo.read("GetRepo", {"repo": repo})

    @mcp.tool()
    async def create_repo(name: str, config: dict[str, Any] | None = None) -> Any:
        """Create a new repository."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateRepo", params)

    @mcp.tool()
    async def update_repo(id: str, config: dict[str, Any]) -> Any:
        """Update repository configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateRepo", {"id": id, "config": config})

    @mcp.tool()
    async def delete_repo(id: str) -> Any:
        """Delete a repository by id or name."""
        return await komodo.write("DeleteRepo", {"id": id})

    @mcp.tool()
    async def clone_repo(repo: str) -> Any:
        """Clone a repository to its target server."""
        return await komodo.execute("CloneRepo", {"repo": repo})

    @mcp.tool()
    async def pull_repo(repo: str) -> Any:
        """Pull latest changes for a repository on its target server."""
        return await komodo.execute("PullRepo", {"repo": repo})
