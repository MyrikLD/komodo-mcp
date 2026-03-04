import pytest
from mcp.server.auth.provider import AuthorizationParams, AuthorizeError
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl
from starlette.requests import Request

from komodo_mcp.oauth import KomodoOAuthProvider

BASE_URL = "http://localhost:8000"
JWT_SECRET = "test-secret-key-long-enough"
PASSWORD = "hunter2"
REDIRECT_URI = AnyUrl("http://localhost:9000/callback")


def _make_auth_params(**kwargs) -> AuthorizationParams:
    defaults = dict(
        state=None,
        scopes=["mcp"],
        code_challenge="ch",
        redirect_uri=REDIRECT_URI,
        redirect_uri_provided_explicitly=True,
    )
    return AuthorizationParams(**(defaults | kwargs))


def _make_login_request(pending_id: str, password: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/login",
        "query_string": b"",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }

    async def receive():
        return {
            "type": "http.request",
            "body": f"id={pending_id}&password={password}".encode(),
        }

    return Request(scope, receive)


@pytest.fixture
def provider():
    return KomodoOAuthProvider(
        base_url=BASE_URL, jwt_secret=JWT_SECRET, password=PASSWORD
    )


@pytest.fixture
def client_info():
    return OAuthClientInformationFull(
        client_id="test-client",
        client_name="Test",
        redirect_uris=[REDIRECT_URI],
        scope="mcp",
    )


@pytest.fixture
async def registered(provider, client_info):
    await provider.register_client(client_info)
    return client_info


# --- client registration ---


async def test_register_and_get_client(provider):
    info = OAuthClientInformationFull(
        client_id="my-client",
        client_name="My App",
        redirect_uris=[REDIRECT_URI],
    )
    await provider.register_client(info)
    found = await provider.get_client("my-client")
    assert found is not None and found.client_id == "my-client"


# --- authorize ---


async def test_authorize_creates_pending_and_redirects_to_login(provider, registered):
    url = await provider.authorize(registered, _make_auth_params())
    assert url.startswith(f"{BASE_URL}/login?id=")
    assert len(provider._pending) == 1


async def test_authorize_unregistered_client_raises(provider, client_info):
    with pytest.raises(AuthorizeError):
        await provider.authorize(client_info, _make_auth_params())


# --- login ---


async def test_login_correct_password_issues_code(provider, registered):
    login_url = await provider.authorize(registered, _make_auth_params(state="s1"))
    pending_id = login_url.split("id=")[1]

    response = await provider._login_post(_make_login_request(pending_id, PASSWORD))

    assert response.status_code == 302
    location = response.headers["location"]
    assert "code=" in location
    assert "state=s1" in location
    assert pending_id not in provider._pending
    assert len(provider._auth_codes) == 1


async def test_login_wrong_password_returns_401(provider, registered):
    login_url = await provider.authorize(registered, _make_auth_params())
    pending_id = login_url.split("id=")[1]

    response = await provider._login_post(_make_login_request(pending_id, "wrong"))

    assert response.status_code == 401
    assert pending_id in provider._pending  # not consumed


async def test_login_expired_pending_returns_400(provider, registered):
    login_url = await provider.authorize(registered, _make_auth_params())
    pending_id = login_url.split("id=")[1]
    provider._pending[pending_id].expires_at = 0  # force expiry

    response = await provider._login_post(_make_login_request(pending_id, PASSWORD))
    assert response.status_code == 400


# --- token exchange ---


async def _do_full_login(provider, registered) -> str:
    """Returns auth code string after a successful login."""
    login_url = await provider.authorize(registered, _make_auth_params())
    pending_id = login_url.split("id=")[1]
    await provider._login_post(_make_login_request(pending_id, PASSWORD))
    return next(iter(provider._auth_codes))


async def test_exchange_code_issues_tokens(provider, registered):
    code_str = await _do_full_login(provider, registered)
    auth_code = provider._auth_codes[code_str]

    token = await provider.exchange_authorization_code(registered, auth_code)

    assert token.access_token and token.refresh_token
    assert token.token_type == "Bearer"
    assert code_str not in provider._auth_codes


async def test_exchange_code_twice_raises(provider, registered):
    from mcp.server.auth.provider import TokenError

    code_str = await _do_full_login(provider, registered)
    auth_code = provider._auth_codes[code_str]
    await provider.exchange_authorization_code(registered, auth_code)

    with pytest.raises(TokenError):
        await provider.exchange_authorization_code(registered, auth_code)


# --- access token ---


async def test_load_valid_access_token(provider, registered):
    code_str = await _do_full_login(provider, registered)
    token = await provider.exchange_authorization_code(
        registered, provider._auth_codes[code_str]
    )

    access = await provider.load_access_token(token.access_token)
    assert access is not None and access.client_id == "test-client"


# --- revocation ---


async def test_revoke_access_token_removes_pair(provider, registered):
    code_str = await _do_full_login(provider, registered)
    token = await provider.exchange_authorization_code(
        registered, provider._auth_codes[code_str]
    )

    access = await provider.load_access_token(token.access_token)
    await provider.revoke_token(access)

    assert await provider.load_access_token(token.access_token) is None
    assert token.refresh_token not in provider._refresh_tokens


async def test_revoke_refresh_token_removes_pair(provider, registered):
    code_str = await _do_full_login(provider, registered)
    token = await provider.exchange_authorization_code(
        registered, provider._auth_codes[code_str]
    )

    refresh = provider._refresh_tokens[token.refresh_token]
    await provider.revoke_token(refresh)

    assert token.refresh_token not in provider._refresh_tokens
    assert await provider.load_access_token(token.access_token) is None
