import os

import httpx
import pytest

os.environ.setdefault("KOMODO_MCP_KOMODO_URL", "http://komodo.test")
os.environ.setdefault("KOMODO_MCP_KOMODO_API_KEY", "test-key")
os.environ.setdefault("KOMODO_MCP_KOMODO_API_SECRET", "test-secret")


@pytest.fixture
def komodo_client(monkeypatch):
    """Provide a KomodoClient with a mocked httpx transport."""
    from komodo_mcp.client import KomodoClient

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json={}))
    client = httpx.AsyncClient(
        transport=transport,
        base_url="http://komodo.test",
    )
    return KomodoClient(client)
