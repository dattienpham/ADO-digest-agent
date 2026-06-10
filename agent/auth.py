import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class BearerAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        key = os.environ.get("MCP_API_KEY", "")
        if key:
            token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not hmac.compare_digest(token, key):
                return Response("Unauthorized", status_code=401)
        return await call_next(request)
