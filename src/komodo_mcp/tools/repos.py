from typing import Any

from fastmcp import FastMCP

from komodo_mcp.client import KomodoClient, KomodoDep


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def list_repos(komodo: KomodoClient = KomodoDep) -> Any:
        """List all repositories in Komodo."""
        return await komodo.read("ListRepos")

    @mcp.tool
    async def get_repo(repo: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Get detailed info about a repository by id or name."""
        return await komodo.read("GetRepo", {"repo": repo})

    @mcp.tool
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

    @mcp.tool
    async def update_repo(
        id: str, config: dict[str, Any], komodo: KomodoClient = KomodoDep
    ) -> Any:
        """Update repository configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateRepo", {"id": id, "config": config})

    @mcp.tool
    async def delete_repo(id: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Delete a repository by id or name."""
        return await komodo.write("DeleteRepo", {"id": id})

    @mcp.tool
    async def clone_repo(repo: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Clone a repository to its target server."""
        return await komodo.execute("CloneRepo", {"repo": repo})

    @mcp.tool
    async def pull_repo(repo: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Pull latest changes for a repository on its target server."""
        return await komodo.execute("PullRepo", {"repo": repo})
