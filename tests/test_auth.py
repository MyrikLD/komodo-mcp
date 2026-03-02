import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from komodo_mcp.auth import BearerTokenMiddleware

TOKEN = "test-secret-token"


def _make_client() -> httpx.AsyncClient:
    async def hello(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", hello)])
    app.add_middleware(BearerTokenMiddleware, token=TOKEN)
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_request_without_token_returns_401() -> None:
    async with _make_client() as client:
        resp = await client.get("/")
    assert resp.status_code == 401
    assert "missing" in resp.json()["error"]


async def test_request_with_wrong_token_returns_401() -> None:
    async with _make_client() as client:
        resp = await client.get("/", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["error"]


async def test_request_with_valid_token_passes() -> None:
    async with _make_client() as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200
    assert resp.text == "ok"
