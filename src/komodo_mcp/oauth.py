import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from authlib.jose.errors import JoseError
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from fastmcp.server.auth import OAuthProvider
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.jwt_issuer import JWTIssuer, derive_jwt_key

logger = logging.getLogger(__name__)

ACCESS_TOKEN_TTL = 3600  # 1 hour
REFRESH_TOKEN_TTL = 30 * 24 * 3600  # 30 days
AUTH_CODE_TTL = 300  # 5 minutes
PENDING_TTL = 600  # 10 minutes to complete login


@dataclass
class PendingAuth:
    client_id: str
    params: AuthorizationParams
    scopes: list[str]
    expires_at: float


_LOGIN_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Komodo MCP — Sign in</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #e2e8f0;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px;
             padding: 2rem; width: 100%; max-width: 360px; }}
    h1 {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 1.5rem; color: #f1f5f9; }}
    label {{ display: block; font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.375rem; }}
    input[type=password] {{ width: 100%; padding: 0.625rem 0.75rem; background: #0f172a;
                            border: 1px solid #334155; border-radius: 6px; color: #f1f5f9;
                            font-size: 0.875rem; outline: none; }}
    input[type=password]:focus {{ border-color: #6366f1; }}
    button {{ width: 100%; margin-top: 1.25rem; padding: 0.625rem;
              background: #6366f1; border: none; border-radius: 6px;
              color: #fff; font-size: 0.875rem; font-weight: 500; cursor: pointer; }}
    button:hover {{ background: #4f46e5; }}
    .error {{ margin-top: 1rem; padding: 0.5rem 0.75rem; background: #450a0a;
              border: 1px solid #991b1b; border-radius: 6px;
              color: #fca5a5; font-size: 0.8125rem; }}
    .meta {{ margin-top: 1rem; font-size: 0.75rem; color: #475569; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Komodo MCP</h1>
    <form method="post">
      <input type="hidden" name="id" value="{pending_id}">
      <label for="pw">Password</label>
      <input type="password" id="pw" name="password" autofocus required>
      <button type="submit">Sign in</button>
      {error_block}
    </form>
    <p class="meta">Client: {client_id}</p>
  </div>
</body>
</html>
"""


class KomodoOAuthProvider(OAuthProvider):
    """Full in-process OAuth 2.1 authorization server with login page."""

    def __init__(self, base_url: str, jwt_secret: str, password: str) -> None:
        super().__init__(
            base_url=base_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
                valid_scopes=["mcp"],
                default_scopes=["mcp"],
            ),
            revocation_options=RevocationOptions(enabled=True),
        )
        self._base_url = base_url.rstrip("/")
        self._password = password

        signing_key = derive_jwt_key(
            high_entropy_material=jwt_secret, salt="komodo-mcp-jwt"
        )
        self._jwt = JWTIssuer(
            issuer=base_url,
            audience=base_url,
            signing_key=signing_key,
        )
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._refresh_tokens: dict[str, RefreshToken] = {}
        self._access_tokens: dict[str, AccessToken] = {}
        self._token_to_jti: dict[str, str] = {}
        self._access_to_refresh: dict[str, str] = {}
        self._refresh_to_access: dict[str, str] = {}
        self._pending: dict[str, PendingAuth] = {}

    # ------------------------------------------------------------------
    # Login page routes (injected via get_routes)
    # ------------------------------------------------------------------

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        routes = super().get_routes(mcp_path)
        routes += [
            Route("/login", endpoint=self._login, methods=["GET", "POST"]),
        ]
        return routes

    async def _login(self, request: Request) -> Response:
        if request.method == "GET":
            pending_id = request.query_params.get("id", "")
            pending = self._pending.get(pending_id)
            if not pending or pending.expires_at < time.time():
                logger.warning(
                    "login GET: invalid or expired pending_id=%s",
                    pending_id[:8] if pending_id else "",
                )
                return HTMLResponse(
                    "<h3>Authorization request expired. Please try again.</h3>",
                    status_code=400,
                )
            html = _LOGIN_HTML.format(
                pending_id=pending_id,
                client_id=pending.client_id,
                error_block="",
            )
            return HTMLResponse(html)
        return await self._login_post(request)

    async def _login_post(self, request: Request) -> Response:
        form = await request.form()
        pending_id = str(form.get("id", ""))
        password = str(form.get("password", ""))

        pending = self._pending.get(pending_id)
        if not pending or pending.expires_at < time.time():
            logger.warning(
                "login POST: invalid or expired pending_id=%s",
                pending_id[:8] if pending_id else "",
            )
            return HTMLResponse(
                "<h3>Authorization request expired. Please try again.</h3>",
                status_code=400,
            )

        if not secrets.compare_digest(password, self._password):
            logger.warning(
                "login POST: wrong password for client_id=%s", pending.client_id
            )
            html = _LOGIN_HTML.format(
                pending_id=pending_id,
                client_id=pending.client_id,
                error_block='<p class="error">Incorrect password.</p>',
            )
            return HTMLResponse(html, status_code=401)

        del self._pending[pending_id]

        code = secrets.token_urlsafe(32)
        self._auth_codes[code] = AuthorizationCode(
            code=code,
            client_id=pending.client_id,
            redirect_uri=pending.params.redirect_uri,
            redirect_uri_provided_explicitly=pending.params.redirect_uri_provided_explicitly,
            scopes=pending.scopes,
            expires_at=time.time() + AUTH_CODE_TTL,
            code_challenge=pending.params.code_challenge,
        )
        redirect = construct_redirect_uri(
            str(pending.params.redirect_uri), code=code, state=pending.params.state
        )
        logger.info(
            "login POST: success client_id=%s code=%s... redirect=%s",
            pending.client_id,
            code[:8],
            redirect[:80],
        )
        return RedirectResponse(redirect, status_code=302)

    # ------------------------------------------------------------------
    # OAuth provider methods
    # ------------------------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        client = self._clients.get(client_id)
        logger.debug("get_client client_id=%s found=%s", client_id, client is not None)
        return client

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id is None:
            raise ValueError("client_id required")
        logger.info(
            "register_client client_id=%s redirect_uris=%s scope=%s",
            client_info.client_id,
            client_info.redirect_uris,
            client_info.scope,
        )
        self._clients[client_info.client_id] = client_info

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        logger.info(
            "authorize client_id=%s redirect_uri=%s scopes=%s state=%s",
            client.client_id,
            params.redirect_uri,
            params.scopes,
            params.state,
        )
        if client.client_id not in self._clients:
            logger.warning(
                "authorize rejected: client_id=%s not registered", client.client_id
            )
            raise AuthorizeError(
                error="unauthorized_client",
                error_description="Client not registered",
            )

        scopes = list(params.scopes or [])
        if client.scope:
            allowed = set(client.scope.split())
            scopes = [s for s in scopes if s in allowed] or list(allowed)

        pending_id = secrets.token_urlsafe(32)
        self._pending[pending_id] = PendingAuth(
            client_id=client.client_id,
            params=params,
            scopes=scopes,
            expires_at=time.time() + PENDING_TTL,
        )
        login_url = f"{self._base_url}/login?{urlencode({'id': pending_id})}"
        logger.info(
            "authorize → login page pending_id=%s... login_url=%s",
            pending_id[:8],
            login_url,
        )
        return login_url

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        entry = self._auth_codes.get(authorization_code)
        if not entry or entry.client_id != client.client_id:
            logger.debug(
                "load_authorization_code code=%s... not found", authorization_code[:8]
            )
            return None
        if entry.expires_at < time.time():
            logger.debug(
                "load_authorization_code code=%s... expired", authorization_code[:8]
            )
            del self._auth_codes[authorization_code]
            return None
        logger.debug("load_authorization_code code=%s... OK", authorization_code[:8])
        return entry

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        logger.info(
            "exchange_authorization_code client_id=%s code=%s...",
            client.client_id,
            authorization_code.code[:8],
        )
        if authorization_code.code not in self._auth_codes:
            logger.warning("exchange_authorization_code: code already used or expired")
            raise TokenError("invalid_grant", "Code already used or expired")
        del self._auth_codes[authorization_code.code]
        if client.client_id is None:
            raise TokenError("invalid_client", "Missing client_id")
        token = self._issue_token_pair(client.client_id, authorization_code.scopes)
        logger.info(
            "exchange_authorization_code issued access_token=%s... scopes=%s",
            token.access_token[:16],
            token.scope,
        )
        return token

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        entry = self._refresh_tokens.get(refresh_token)
        if not entry or entry.client_id != client.client_id:
            logger.debug(
                "load_refresh_token: not found for client_id=%s", client.client_id
            )
            return None
        if entry.expires_at is not None and entry.expires_at < time.time():
            logger.debug(
                "load_refresh_token: expired for client_id=%s", client.client_id
            )
            del self._refresh_tokens[refresh_token]
            return None
        logger.debug("load_refresh_token OK client_id=%s", client.client_id)
        return entry

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        logger.info(
            "exchange_refresh_token client_id=%s scopes=%s", client.client_id, scopes
        )
        if scopes and not set(scopes).issubset(set(refresh_token.scopes)):
            raise TokenError("invalid_scope", "Requested scopes exceed original grant")
        effective_scopes = scopes or refresh_token.scopes
        self._revoke_pair(refresh_token_str=refresh_token.token)
        if client.client_id is None:
            raise TokenError("invalid_client", "Missing client_id")
        token = self._issue_token_pair(client.client_id, effective_scopes)
        logger.info(
            "exchange_refresh_token issued access_token=%s... scopes=%s",
            token.access_token[:16],
            token.scope,
        )
        return token

    async def load_access_token(self, token: str) -> AccessToken | None:
        try:
            claims = self._jwt.verify_token(token)
        except JoseError as e:
            logger.debug("load_access_token JWT invalid: %s", e)
            return None
        jti = claims.get("jti")
        if not jti:
            logger.debug("load_access_token: no jti in claims")
            return None
        access = self._access_tokens.get(jti)
        logger.debug(
            "load_access_token jti=%s... found=%s client_id=%s",
            jti[:8],
            access is not None,
            access.client_id if access else None,
        )
        return access

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        logger.info("revoke_token type=%s", type(token).__name__)
        if isinstance(token, AccessToken):
            self._revoke_pair(access_token_str=token.token)
        else:
            self._revoke_pair(refresh_token_str=token.token)

    # ------------------------------------------------------------------

    def _issue_token_pair(self, client_id: str, scopes: list[str]) -> OAuthToken:
        now = int(time.time())

        jti = secrets.token_urlsafe(32)
        access_str = self._jwt.issue_access_token(
            client_id=client_id,
            scopes=scopes,
            jti=jti,
            expires_in=ACCESS_TOKEN_TTL,
        )
        self._access_tokens[jti] = AccessToken(
            token=access_str,
            client_id=client_id,
            scopes=scopes,
            expires_at=now + ACCESS_TOKEN_TTL,
        )
        self._token_to_jti[access_str] = jti

        refresh_jti = secrets.token_urlsafe(32)
        refresh_str = self._jwt.issue_refresh_token(
            client_id=client_id,
            scopes=scopes,
            jti=refresh_jti,
            expires_in=REFRESH_TOKEN_TTL,
        )
        self._refresh_tokens[refresh_str] = RefreshToken(
            token=refresh_str,
            client_id=client_id,
            scopes=scopes,
            expires_at=now + REFRESH_TOKEN_TTL,
        )
        self._access_to_refresh[access_str] = refresh_str
        self._refresh_to_access[refresh_str] = access_str

        return OAuthToken(
            access_token=access_str,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL,
            refresh_token=refresh_str,
            scope=" ".join(scopes),
        )

    def _revoke_pair(
        self,
        access_token_str: str | None = None,
        refresh_token_str: str | None = None,
    ) -> None:
        if access_token_str:
            jti = self._token_to_jti.pop(access_token_str, None)
            if jti:
                self._access_tokens.pop(jti, None)
            paired_refresh = self._access_to_refresh.pop(access_token_str, None)
            if paired_refresh:
                self._refresh_tokens.pop(paired_refresh, None)
                self._refresh_to_access.pop(paired_refresh, None)

        if refresh_token_str:
            self._refresh_tokens.pop(refresh_token_str, None)
            paired_access = self._refresh_to_access.pop(refresh_token_str, None)
            if paired_access:
                jti = self._token_to_jti.pop(paired_access, None)
                if jti:
                    self._access_tokens.pop(jti, None)
                self._access_to_refresh.pop(paired_access, None)
