from typing import Any

from fastmcp import FastMCP

from komodo_mcp.client import KomodoClient, KomodoDep


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def get_version(komodo: KomodoClient = KomodoDep) -> Any:
        """Get the Komodo Core API version."""
        return await komodo.read("GetVersion")

    @mcp.tool
    async def get_system_info(server: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Get system information (OS, CPU, memory, disks) for a server."""
        return await komodo.read("GetSystemInformation", {"server": server})

    @mcp.tool
    async def list_updates(komodo: KomodoClient = KomodoDep) -> Any:
        """List recent updates/actions in Komodo."""
        return await komodo.read("ListUpdates")

    @mcp.tool
    async def list_alerters(komodo: KomodoClient = KomodoDep) -> Any:
        """List all alerters in Komodo."""
        return await komodo.read("ListAlerters")

    @mcp.tool
    async def get_alerter(alerter: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Get detailed info about an alerter by id or name."""
        return await komodo.read("GetAlerter", {"alerter": alerter})

    @mcp.tool
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

    @mcp.tool
    async def update_alerter(
        id: str, config: dict[str, Any], komodo: KomodoClient = KomodoDep
    ) -> Any:
        """Update alerter configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateAlerter", {"id": id, "config": config})

    @mcp.tool
    async def delete_alerter(id: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Delete an alerter by id or name."""
        return await komodo.write("DeleteAlerter", {"id": id})
