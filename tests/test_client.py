import json

import httpx
import pytest

from komodo_mcp.client import KomodoClient


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="http://komodo.test")
    return KomodoClient(http)


async def test_read_sends_correct_payload():
    captured = {}

    def handler(request: httpx.Request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=[{"name": "amber"}])

    client = make_client(handler)
    result = await client.read("ListServers")

    assert captured["url"] == "http://komodo.test/read"
    assert captured["body"] == {"type": "ListServers", "params": {}}
    assert result == [{"name": "amber"}]


async def test_write_sends_correct_payload():
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "123"})

    client = make_client(handler)
    result = await client.write("CreateServer", {"name": "test-server"})

    assert captured["body"] == {
        "type": "CreateServer",
        "params": {"name": "test-server"},
    }
    assert result == {"id": "123"}


async def test_execute_sends_correct_payload():
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "ok"})

    client = make_client(handler)
    result = await client.execute("DeployStack", {"stack": "my-stack"})

    assert captured["body"] == {
        "type": "DeployStack",
        "params": {"stack": "my-stack"},
    }
    assert result == {"status": "ok"}


async def test_read_with_params():
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"name": "amber"})

    client = make_client(handler)
    await client.read("GetServer", {"server": "amber"})

    assert captured["body"] == {"type": "GetServer", "params": {"server": "amber"}}


def busy_response():
    return httpx.Response(500, json={"error": "Stack busy", "trace": []})


async def test_busy_is_retried_until_the_lock_clears(monkeypatch):
    monkeypatch.setattr("komodo_mcp.client._BUSY_BACKOFF", (0, 0, 0))
    attempts = []

    def handler(request: httpx.Request):
        attempts.append(request)
        if len(attempts) < 3:
            return busy_response()
        return httpx.Response(200, json={"status": "ok"})

    client = make_client(handler)
    result = await client.write("UpdateStack", {"id": "abc"})

    assert len(attempts) == 3
    assert result == {"status": "ok"}


async def test_busy_gives_up_with_an_actionable_message(monkeypatch):
    monkeypatch.setattr("komodo_mcp.client._BUSY_BACKOFF", (0, 0, 0))
    attempts = []

    def handler(request: httpx.Request):
        attempts.append(request)
        return busy_response()

    client = make_client(handler)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.write("UpdateStack", {"id": "abc"})

    assert len(attempts) == 4
    assert "Stack busy" in str(exc_info.value)
    assert "retry" in str(exc_info.value)


async def test_other_errors_surface_the_response_body_without_retrying():
    attempts = []

    def handler(request: httpx.Request):
        attempts.append(request)
        return httpx.Response(422, json={"error": "invalid config"})

    client = make_client(handler)
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.write("UpdateStack", {"id": "abc"})

    assert len(attempts) == 1
    assert "invalid config" in str(exc_info.value)
