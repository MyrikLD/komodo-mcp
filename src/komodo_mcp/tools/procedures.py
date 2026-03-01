from typing import Any

from mcp.server.fastmcp import FastMCP

from komodo_mcp.client import komodo


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_procedures() -> Any:
        """List all procedures in Komodo."""
        return await komodo.read("ListProcedures")

    @mcp.tool()
    async def get_procedure(procedure: str) -> Any:
        """Get detailed info about a procedure by id or name."""
        return await komodo.read("GetProcedure", {"procedure": procedure})

    @mcp.tool()
    async def create_procedure(name: str, config: dict[str, Any] | None = None) -> Any:
        """Create a new procedure."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateProcedure", params)

    @mcp.tool()
    async def update_procedure(id: str, config: dict[str, Any]) -> Any:
        """Update procedure configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateProcedure", {"id": id, "config": config})

    @mcp.tool()
    async def delete_procedure(id: str) -> Any:
        """Delete a procedure by id or name."""
        return await komodo.write("DeleteProcedure", {"id": id})

    @mcp.tool()
    async def run_procedure(procedure: str) -> Any:
        """Run a procedure."""
        return await komodo.execute("RunProcedure", {"procedure": procedure})
