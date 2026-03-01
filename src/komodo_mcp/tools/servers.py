from typing import Any

from fastmcp import FastMCP

from komodo_mcp.client import KomodoClient, KomodoDep


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def list_servers(komodo: KomodoClient = KomodoDep) -> Any:
        """List all servers in Komodo."""
        return await komodo.read("ListServers")

    @mcp.tool
    async def get_server(server: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Get detailed info about a server by id or name."""
        return await komodo.read("GetServer", {"server": server})

    @mcp.tool
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

    @mcp.tool
    async def update_server(
        id: str, config: dict[str, Any], komodo: KomodoClient = KomodoDep
    ) -> Any:
        """Update server configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateServer", {"id": id, "config": config})

    @mcp.tool
    async def delete_server(id: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Delete a server by id or name."""
        return await komodo.write("DeleteServer", {"id": id})

    @mcp.tool
    async def get_server_stats(server: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Get system stats (CPU, memory, disk) for a server."""
        return await komodo.read("GetSystemStats", {"server": server})
