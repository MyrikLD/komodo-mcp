import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Validates Bearer token on every request if AUTH_TOKEN is configured."""

    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self.token = token

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "missing bearer token"}, status_code=401)
        provided = auth_header[7:]
        if not secrets.compare_digest(provided, self.token):
            return JSONResponse({"error": "invalid token"}, status_code=401)
        return await call_next(request)
