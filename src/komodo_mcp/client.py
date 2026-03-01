from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import httpx

from komodo_mcp.config import settings


class KomodoClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        async with httpx.AsyncClient(
            base_url=settings.KOMODO_URL.rstrip("/"),
            headers={
                "X-Api-Key": settings.KOMODO_API_KEY,
                "X-Api-Secret": settings.KOMODO_API_SECRET,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        ) as c:
            self._client = c
            yield
        self._client = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Komodo client not initialized.")
        return self._client

    async def _request(
        self, endpoint: str, operation: str, params: dict[str, Any]
    ) -> Any:
        response = await self.http.post(
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


komodo = KomodoClient()
