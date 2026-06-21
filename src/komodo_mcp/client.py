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
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Komodo returns the validation/error detail in the response body;
            # surface it so callers see *why* a request failed (e.g. 422).
            detail = response.text.strip()
            message = f"Komodo {operation} failed: {exc}"
            if detail:
                message = f"{message}\n{detail}"
            raise httpx.HTTPStatusError(
                message, request=exc.request, response=exc.response
            ) from exc
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
