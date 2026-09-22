import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastmcp.dependencies import Depends

from komodo_mcp.config import settings

# Komodo holds a per-resource lock while an action runs and answers
# `500 {"error": "Stack busy"}` to anything else touching it meanwhile.
_BUSY_BACKOFF = (1.0, 2.0, 4.0)


def _busy_reason(detail: str) -> str | None:
    try:
        error = json.loads(detail).get("error")
    except (ValueError, AttributeError):
        return None
    if isinstance(error, str) and error.lower().endswith(" busy"):
        return error
    return None


def _failure(
    operation: str, response: httpx.Response, detail: str
) -> httpx.HTTPStatusError:
    busy = _busy_reason(detail)
    if busy:
        message = (
            f"Komodo {operation} failed: {busy} — another action on it is still "
            f"running. Wait for it to finish and retry."
        )
    else:
        # Komodo returns the validation/error detail in the response body;
        # surface it so callers see *why* a request failed (e.g. 422).
        message = f"Komodo {operation} failed: HTTP {response.status_code}"
        if detail:
            message = f"{message}\n{detail}"
    return httpx.HTTPStatusError(message, request=response.request, response=response)


class KomodoClient:
    _client: httpx.AsyncClient

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _request(
        self, endpoint: str, operation: str, params: dict[str, Any]
    ) -> Any:
        for delay in (*_BUSY_BACKOFF, None):
            response = await self._client.post(
                endpoint,
                json={"type": operation, "params": params},
            )
            if response.is_success:
                return response.json()
            detail = response.text.strip()
            if delay is not None and _busy_reason(detail):
                await asyncio.sleep(delay)
                continue
            raise _failure(operation, response, detail)

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
