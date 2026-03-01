from typing import Any

from mcp.server.fastmcp import FastMCP

from komodo_mcp.client import komodo


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_stacks() -> Any:
        """List all stacks in Komodo."""
        return await komodo.read("ListStacks")

    @mcp.tool()
    async def get_stack(stack: str) -> Any:
        """Get detailed info about a stack by id or name."""
        return await komodo.read("GetStack", {"stack": stack})

    @mcp.tool()
    async def get_stack_log(stack: str) -> Any:
        """Get logs for a stack."""
        return await komodo.read("GetStackLog", {"stack": stack})

    @mcp.tool()
    async def create_stack(name: str, config: dict[str, Any] | None = None) -> Any:
        """Create a new stack."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateStack", params)

    @mcp.tool()
    async def update_stack(id: str, config: dict[str, Any]) -> Any:
        """Update stack configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateStack", {"id": id, "config": config})

    @mcp.tool()
    async def delete_stack(id: str) -> Any:
        """Delete a stack by id or name."""
        return await komodo.write("DeleteStack", {"id": id})

    @mcp.tool()
    async def deploy_stack(
        stack: str,
        services: list[str] | None = None,
        stop_time: int | None = None,
    ) -> Any:
        """Deploy a stack (docker compose up). Optionally specify services and stop timeout."""
        params: dict[str, Any] = {"stack": stack}
        if services:
            params["services"] = services
        if stop_time is not None:
            params["stop_time"] = stop_time
        return await komodo.execute("DeployStack", params)

    @mcp.tool()
    async def start_stack(stack: str, services: list[str] | None = None) -> Any:
        """Start a stack (docker compose start)."""
        params: dict[str, Any] = {"stack": stack}
        if services:
            params["services"] = services
        return await komodo.execute("StartStack", params)

    @mcp.tool()
    async def stop_stack(
        stack: str,
        services: list[str] | None = None,
        stop_time: int | None = None,
    ) -> Any:
        """Stop a stack (docker compose stop)."""
        params: dict[str, Any] = {"stack": stack}
        if services:
            params["services"] = services
        if stop_time is not None:
            params["stop_time"] = stop_time
        return await komodo.execute("StopStack", params)

    @mcp.tool()
    async def restart_stack(stack: str, services: list[str] | None = None) -> Any:
        """Restart a stack (docker compose restart)."""
        params: dict[str, Any] = {"stack": stack}
        if services:
            params["services"] = services
        return await komodo.execute("RestartStack", params)
