from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp.dependencies import Depends

from komodo_mcp.config import settings


class KomodoClient:
    _client: httpx.AsyncClient

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _request(
        self, endpoint: str, operation: str, params: dict[str, Any]
    ) -> Any:
        response = await self._client.post(
            endpoint,
            json={"type": operation, "params": params},
        )
        response.raise_for_status()
        return response.json()

    async def read(self, operation: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("/read", operation, params or {})

    async def write(self, operation: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("/write", operation, params or {})

    async def execute(
        self, operation: str, params: dict[str, Any] | None = None
    ) -> Any:
        return await self._request("/execute", operation, params or {})


@asynccontextmanager
async def get_komodo() -> KomodoClient:
    async with httpx.AsyncClient(
        base_url=settings.KOMODO_URL.rstrip("/"),
        headers={
            "X-Api-Key": settings.KOMODO_API_KEY,
            "X-Api-Secret": settings.KOMODO_API_SECRET,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    ) as c:
        yield KomodoClient(c)


KomodoDep = Depends(get_komodo)
