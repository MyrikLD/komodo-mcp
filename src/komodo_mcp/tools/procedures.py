from typing import Any

from fastmcp import FastMCP

from komodo_mcp.client import KomodoClient, KomodoDep


def register(mcp: FastMCP) -> None:
    @mcp.tool
    async def list_procedures(komodo: KomodoClient = KomodoDep) -> Any:
        """List all procedures in Komodo."""
        return await komodo.read("ListProcedures")

    @mcp.tool
    async def get_procedure(procedure: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Get detailed info about a procedure by id or name."""
        return await komodo.read("GetProcedure", {"procedure": procedure})

    @mcp.tool
    async def create_procedure(
        name: str,
        config: dict[str, Any] | None = None,
        komodo: KomodoClient = KomodoDep,
    ) -> Any:
        """Create a new procedure."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateProcedure", params)

    @mcp.tool
    async def update_procedure(
        id: str, config: dict[str, Any], komodo: KomodoClient = KomodoDep
    ) -> Any:
        """Update procedure configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateProcedure", {"id": id, "config": config})

    @mcp.tool
    async def delete_procedure(id: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Delete a procedure by id or name."""
        return await komodo.write("DeleteProcedure", {"id": id})

    @mcp.tool
    async def run_procedure(procedure: str, komodo: KomodoClient = KomodoDep) -> Any:
        """Run a procedure."""
        return await komodo.execute("RunProcedure", {"procedure": procedure})
