"""
security.py — Security headers middleware.

Adds standard HTTP security headers to every response to harden the API
against common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Headers added to every response
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that injects security headers into every HTTP response.

    Headers are non-destructive: they are only added when not already present.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            if header not in response.headers:
                response.headers[header] = value
        return response
