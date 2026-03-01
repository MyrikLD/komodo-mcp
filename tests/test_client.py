import json

import httpx

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
