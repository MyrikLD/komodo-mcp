from typing import Any

from mcp.server.fastmcp import FastMCP

from komodo_mcp.client import komodo


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_deployments() -> Any:
        """List all deployments in Komodo."""
        return await komodo.read("ListDeployments")

    @mcp.tool()
    async def get_deployment(deployment: str) -> Any:
        """Get detailed info about a deployment by id or name."""
        return await komodo.read("GetDeployment", {"deployment": deployment})

    @mcp.tool()
    async def get_deployment_log(deployment: str) -> Any:
        """Get logs for a deployment."""
        return await komodo.read("GetDeploymentLog", {"deployment": deployment})

    @mcp.tool()
    async def create_deployment(name: str, config: dict[str, Any] | None = None) -> Any:
        """Create a new deployment."""
        params: dict[str, Any] = {"name": name}
        if config:
            params["config"] = config
        return await komodo.write("CreateDeployment", params)

    @mcp.tool()
    async def update_deployment(id: str, config: dict[str, Any]) -> Any:
        """Update deployment configuration. Config is merged, not replaced."""
        return await komodo.write("UpdateDeployment", {"id": id, "config": config})

    @mcp.tool()
    async def delete_deployment(id: str) -> Any:
        """Delete a deployment by id or name."""
        return await komodo.write("DeleteDeployment", {"id": id})

    @mcp.tool()
    async def deploy(
        deployment: str,
        stop_signal: str | None = None,
        stop_time: int | None = None,
    ) -> Any:
        """Deploy a deployment (pull image and recreate container)."""
        params: dict[str, Any] = {"deployment": deployment}
        if stop_signal:
            params["stop_signal"] = stop_signal
        if stop_time is not None:
            params["stop_time"] = stop_time
        return await komodo.execute("Deploy", params)

    @mcp.tool()
    async def start_deployment(deployment: str) -> Any:
        """Start a stopped deployment container."""
        return await komodo.execute("StartDeployment", {"deployment": deployment})

    @mcp.tool()
    async def stop_deployment(deployment: str, stop_time: int | None = None) -> Any:
        """Stop a deployment container."""
        params: dict[str, Any] = {"deployment": deployment}
        if stop_time is not None:
            params["stop_time"] = stop_time
        return await komodo.execute("StopDeployment", params)

    @mcp.tool()
    async def restart_deployment(deployment: str) -> Any:
        """Restart a deployment container."""
        return await komodo.execute("RestartDeployment", {"deployment": deployment})
