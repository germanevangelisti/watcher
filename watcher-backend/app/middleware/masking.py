"""
masking.py — CUIT masking middleware for privacy protection.

Argentine CUITs (Clave Única de Identificación Tributaria) are 11-digit tax
identifiers formatted as XX-XXXXXXXX-X. This middleware intercepts HTTP
responses and replaces any CUIT found in JSON response bodies with a masked
representation (XX-XXXXXXXX-X → **-********-*).

Only applies to JSON responses (Content-Type: application/json).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

# CUIT pattern: two digits, hyphen (optional), eight digits, hyphen (optional), one digit
# Matches: 20-12345678-9 / 20123456789 / 20-123456789 etc.
CUIT_RE = re.compile(r"\b(\d{2})-?(\d{8})-?(\d)\b")

# Replacement uses visible masking to indicate redaction
CUIT_MASK = "**-********-*"


def mask_cuit(text: str) -> str:
    """Replace all CUIT occurrences in *text* with CUIT_MASK."""
    return CUIT_RE.sub(CUIT_MASK, text)


def mask_value(obj: Any) -> Any:
    """
    Recursively mask CUITs in a deserialized JSON structure.

    Handles dicts, lists, and string values.
    """
    if isinstance(obj, dict):
        return {k: mask_value(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_value(item) for item in obj]
    if isinstance(obj, str):
        return mask_cuit(obj)
    return obj


class CUITMaskingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that masks Argentine CUIT numbers in JSON responses.

    Safe to use in production — non-JSON responses are passed through
    unmodified. Masking is applied to the serialised response body.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Consume the response body
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        try:
            text = body_bytes.decode("utf-8")
            masked_text = mask_cuit(text)
            masked_bytes = masked_text.encode("utf-8")
        except Exception:
            # If anything fails, return the original response unmodified
            masked_bytes = body_bytes

        # Exclude Content-Length — it will be wrong after masking changes byte length.
        # Starlette recalculates it automatically from the content.
        headers = {
            k: v for k, v in response.headers.items()
            if k.lower() != "content-length"
        }
        return Response(
            content=masked_bytes,
            status_code=response.status_code,
            headers=headers,
            media_type=content_type,
        )
