"""
Unit tests for SecurityHeadersMiddleware.

Tests validate:
- All required security headers are injected
- Existing headers are not overwritten
- Non-JSON responses also receive headers
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import Response

from app.middleware.security import SECURITY_HEADERS, SecurityHeadersMiddleware


class TestSecurityHeadersConstants:
    def test_x_content_type_options_present(self):
        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_present(self):
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_x_xss_protection_present(self):
        assert "X-XSS-Protection" in SECURITY_HEADERS

    def test_referrer_policy_present(self):
        assert "Referrer-Policy" in SECURITY_HEADERS

    def test_at_least_4_headers(self):
        assert len(SECURITY_HEADERS) >= 4


class TestSecurityHeadersMiddleware:
    """Test middleware dispatch logic via direct async calls (no live ASGI server)."""

    def _make_response(self, extra_headers=None):
        """Build a minimal Starlette Response with optional preset headers."""
        headers = extra_headers or {}
        return Response(content="OK", status_code=200, headers=headers)

    @pytest.mark.anyio
    async def test_middleware_dispatch_adds_headers(self):
        """dispatch() must inject all SECURITY_HEADERS into a plain response."""
        response = self._make_response()
        call_next = AsyncMock(return_value=response)

        mw = SecurityHeadersMiddleware(app=MagicMock())
        mw.dispatch = SecurityHeadersMiddleware.dispatch.__get__(mw, SecurityHeadersMiddleware)

        request = MagicMock()
        result = await SecurityHeadersMiddleware.dispatch(mw, request, call_next)

        for header in SECURITY_HEADERS:
            assert header in result.headers, f"Missing header: {header}"

    @pytest.mark.anyio
    async def test_middleware_does_not_overwrite_existing_header(self):
        """dispatch() must skip headers already set in the response."""
        response = self._make_response({"X-Frame-Options": "SAMEORIGIN"})
        call_next = AsyncMock(return_value=response)
        mw = SecurityHeadersMiddleware(app=MagicMock())

        request = MagicMock()
        result = await SecurityHeadersMiddleware.dispatch(mw, request, call_next)
        assert result.headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_middleware_class_is_importable(self):
        """SecurityHeadersMiddleware must be importable and have dispatch method."""
        assert hasattr(SecurityHeadersMiddleware, "dispatch")
        assert callable(SecurityHeadersMiddleware.dispatch)
