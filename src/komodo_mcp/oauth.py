import hashlib
import hmac
import html
import logging
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from authlib.jose import JsonWebToken
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
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from fastmcp.server.auth import OAuthProvider
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.jwt_issuer import JWTIssuer, derive_jwt_key
from komodo_mcp.revocation import REVOCATION_FILE, RevocationStore

logger = logging.getLogger(__name__)

ACCESS_TOKEN_TTL = 3600  # 1 hour
REFRESH_TOKEN_TTL = 30 * 24 * 3600  # 30 days
AUTH_CODE_TTL = 300  # 5 minutes
PENDING_TTL = 600  # 10 minutes to complete login

CLIENT_TOKEN_USE = "client"
REFRESH_TOKEN_USE = "refresh"

# Both tokens of a pair share a prefix so that revoking one revokes the other
# without any server-side bookkeeping of the pairing.
ACCESS_JTI_SUFFIX = ".a"
REFRESH_JTI_SUFFIX = ".r"

# Client metadata carried inside the client_id JWT (RFC 7591 fields).
CLIENT_METADATA_FIELDS = {
    "redirect_uris",
    "token_endpoint_auth_method",
    "grant_types",
    "response_types",
    "scope",
    "client_name",
    "client_uri",
    "logo_uri",
    "contacts",
    "tos_uri",
    "policy_uri",
    "software_id",
    "software_version",
}


def _pair_id(jti: str) -> str:
    return jti.rsplit(".", 1)[0]


class PendingAuth(BaseModel):
    client_id: str
    client_name: str
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
    <p class="meta">Client: {client_name}</p>
  </div>
</body>
</html>
"""


class KomodoOAuthProvider(OAuthProvider):
    """Full in-process OAuth 2.1 authorization server with login page.

    The provider keeps no long-lived state in memory: access/refresh tokens are
    self-contained JWTs and a registered client's metadata is carried inside its
    ``client_id`` (also a JWT). Everything is signed with a key derived from
    ``jwt_secret``, so tokens and client registrations issued before a restart
    keep working afterwards — clients never have to re-authorize.

    The only state that must outlive the process is the set of revoked tokens;
    it goes to ``state_dir`` when one is configured (see ``RevocationStore``).
    Authorization codes and pending logins live for minutes and stay in memory.
    """

    def __init__(
        self,
        base_url: str,
        jwt_secret: str,
        password: str,
        state_dir: Path | None = None,
    ) -> None:
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

        self._signing_key = derive_jwt_key(
            high_entropy_material=jwt_secret, salt="komodo-mcp-jwt"
        )
        self._jwt = JWTIssuer(
            issuer=base_url,
            audience=base_url,
            signing_key=self._signing_key,
        )
        self._jose = JsonWebToken(["HS256"])
        self._revocations = RevocationStore(
            state_dir / REVOCATION_FILE if state_dir else None
        )
        self._auth_codes: dict[str, AuthorizationCode] = {}
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
            page = _LOGIN_HTML.format(
                pending_id=pending_id,
                client_name=html.escape(pending.client_name),
                error_block="",
            )
            return HTMLResponse(page)
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
                "login POST: wrong password for client=%s", pending.client_name
            )
            page = _LOGIN_HTML.format(
                pending_id=pending_id,
                client_name=html.escape(pending.client_name),
                error_block='<p class="error">Incorrect password.</p>',
            )
            return HTMLResponse(page, status_code=401)

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
            "login POST: success client=%s code=%s... redirect=%s",
            pending.client_name,
            code[:8],
            redirect[:80],
        )
        return RedirectResponse(redirect, status_code=302)

    # ------------------------------------------------------------------
    # OAuth provider methods
    # ------------------------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        client = self._decode_client(client_id)
        logger.debug(
            "get_client client=%s found=%s",
            client.client_name if client else client_id[:16],
            client is not None,
        )
        return client

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        """Replace the SDK-generated credentials with self-contained ones.

        The ``client_id`` handed to us is a random UUID that would only be
        meaningful while this process lives. We swap it for a signed JWT that
        carries the whole registration, and derive the secret from it, so the
        registration can be validated again after a restart without any storage.
        The mutated object is what the /register endpoint returns to the client.
        """
        client_id = self._encode_client(client_info)
        client_info.client_id = client_id
        client_info.client_secret = (
            None
            if client_info.token_endpoint_auth_method == "none"
            else self._client_secret(client_id)
        )
        client_info.client_secret_expires_at = None
        logger.info(
            "register_client client_name=%s redirect_uris=%s scope=%s",
            client_info.client_name,
            client_info.redirect_uris,
            client_info.scope,
        )

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        logger.info(
            "authorize client=%s redirect_uri=%s scopes=%s state=%s",
            client.client_name,
            params.redirect_uri,
            params.scopes,
            params.state,
        )
        registered = self._decode_client(client.client_id or "")
        if registered is None:
            logger.warning("authorize rejected: client not registered")
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
            client_id=registered.client_id or "",
            client_name=registered.client_name or "unknown",
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
            "exchange_authorization_code client=%s code=%s...",
            client.client_name,
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
        claims = self._verify_token(refresh_token, token_use=REFRESH_TOKEN_USE)
        if claims is None:
            logger.debug(
                "load_refresh_token: rejected for client=%s", client.client_name
            )
            return None
        if claims.get("client_id") != client.client_id:
            logger.debug("load_refresh_token: client mismatch")
            return None
        logger.debug("load_refresh_token OK client=%s", client.client_name)
        return RefreshToken(
            token=refresh_token,
            client_id=claims["client_id"],
            scopes=(claims.get("scope") or "").split(),
            expires_at=claims.get("exp"),
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        logger.info(
            "exchange_refresh_token client=%s scopes=%s", client.client_name, scopes
        )
        if scopes and not set(scopes).issubset(set(refresh_token.scopes)):
            raise TokenError("invalid_scope", "Requested scopes exceed original grant")
        effective_scopes = scopes or refresh_token.scopes
        self._revoke(refresh_token.token)
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
        claims = self._verify_token(token, token_use=None)
        if claims is None:
            return None
        logger.debug("load_access_token OK jti=%s...", claims["jti"][:8])
        return AccessToken(
            token=token,
            client_id=claims.get("client_id", ""),
            scopes=(claims.get("scope") or "").split(),
            expires_at=claims.get("exp"),
            claims=claims,
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        logger.info("revoke_token type=%s", type(token).__name__)
        self._revoke(token.token)

    # ------------------------------------------------------------------
    # Stateless client registrations
    # ------------------------------------------------------------------

    def _encode_client(self, client_info: OAuthClientInformationFull) -> str:
        """Pack a client registration into a signed, non-expiring JWT."""
        metadata = client_info.model_dump(
            mode="json", include=CLIENT_METADATA_FIELDS, exclude_none=True
        )
        payload = {
            # Must match what JWTIssuer.verify_token expects, trailing slash included
            "iss": self._jwt.issuer,
            "aud": self._jwt.audience,
            "iat": int(time.time()),
            "token_use": CLIENT_TOKEN_USE,
            "client": metadata,
        }
        header = {"alg": "HS256", "typ": "JWT"}
        return self._jose.encode(header, payload, self._signing_key).decode()

    def _decode_client(self, client_id: str) -> OAuthClientInformationFull | None:
        try:
            claims = self._jwt.verify_token(client_id)
        except JoseError as exc:
            logger.debug("get_client: not a valid client_id: %s", exc)
            return None
        if claims.get("token_use") != CLIENT_TOKEN_USE:
            logger.debug("get_client: token_use is not %s", CLIENT_TOKEN_USE)
            return None
        try:
            client = OAuthClientInformationFull(
                client_id=client_id,
                client_id_issued_at=claims.get("iat"),
                **claims.get("client", {}),
            )
        except ValidationError as exc:
            logger.warning("get_client: malformed client metadata: %s", exc)
            return None
        if client.token_endpoint_auth_method != "none":
            client.client_secret = self._client_secret(client_id)
        return client

    def _client_secret(self, client_id: str) -> str:
        """Derive the client secret from the client_id — no storage needed."""
        return hmac.new(
            self._signing_key, client_id.encode(), hashlib.sha256
        ).hexdigest()

    # ------------------------------------------------------------------
    # Stateless tokens
    # ------------------------------------------------------------------

    def _issue_token_pair(self, client_id: str, scopes: list[str]) -> OAuthToken:
        pair_id = secrets.token_urlsafe(32)
        access_str = self._jwt.issue_access_token(
            client_id=client_id,
            scopes=scopes,
            jti=pair_id + ACCESS_JTI_SUFFIX,
            expires_in=ACCESS_TOKEN_TTL,
        )
        refresh_str = self._jwt.issue_refresh_token(
            client_id=client_id,
            scopes=scopes,
            jti=pair_id + REFRESH_JTI_SUFFIX,
            expires_in=REFRESH_TOKEN_TTL,
        )
        return OAuthToken(
            access_token=access_str,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL,
            refresh_token=refresh_str,
            scope=" ".join(scopes),
        )

    def _verify_token(self, token: str, token_use: str | None) -> dict[str, Any] | None:
        """Validate signature, expiry, kind and revocation; return the claims.

        ``token_use`` is ``None`` for access tokens (the claim is absent) and
        ``"refresh"`` for refresh tokens — matching them exactly is what stops a
        refresh token from being presented as a bearer token, and vice versa.
        """
        try:
            claims = self._jwt.verify_token(token)
        except JoseError as exc:
            logger.debug("token rejected: %s", exc)
            return None
        if claims.get("token_use") != token_use:
            logger.debug(
                "token rejected: token_use=%s, expected %s",
                claims.get("token_use"),
                token_use,
            )
            return None
        jti = claims.get("jti")
        if not jti:
            logger.debug("token rejected: no jti in claims")
            return None
        if self._revocations.is_revoked(_pair_id(jti)):
            logger.debug("token rejected: revoked jti=%s...", jti[:8])
            return None
        return claims

    def _revoke(self, token: str) -> None:
        """Revoke a token and its counterpart from the same issuance."""
        try:
            claims = self._jwt.verify_token(token)
        except JoseError as exc:
            logger.debug("revoke: token not verifiable: %s", exc)
            return
        jti = claims.get("jti")
        if not jti:
            return
        # The access token of a pair expires long before its refresh token, so
        # the entry has to outlive the longest-lived token it can revoke.
        self._revocations.revoke(_pair_id(jti), time.time() + REFRESH_TOKEN_TTL)
        logger.info("revoked token pair jti=%s...", jti[:8])
