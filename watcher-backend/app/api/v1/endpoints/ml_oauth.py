"""Mercado Libre user login (OAuth authorization_code) for precio-mercado.

- ``GET  /precio-mercado/ml/login``     redirects to the ML authorization page
- ``GET  /precio-mercado/ml/callback``  ML redirects here with ``code``; exchanges it
- ``POST /precio-mercado/ml/exchange``  manual exchange: paste the ``code`` from the
  browser address bar when the redirect URI is a static https page
- ``GET  /precio-mercado/ml/status``    token state, never secret values

The refresh token lands in ``watcher-backend/.cache/ml_token.json`` (gitignored).
"""

import base64
import hashlib
import os
import secrets

from app.services.price_sources import MercadoLibreAuth
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter()

# state -> PKCE verifier (None when PKCE is off). In memory: a login is a
# few seconds; restarting the backend just means clicking login again.
_pending: dict[str, str | None] = {}


def redirect_uri() -> str:
    uri = os.getenv("ML_REDIRECT_URI")
    if not uri:
        raise HTTPException(status_code=400, detail="falta ML_REDIRECT_URI en el .env")
    return uri


def _pkce() -> tuple[str | None, str | None]:
    if os.getenv("ML_PKCE", "0") != "1":
        return None, None
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


@router.get("/ml/login")
async def ml_login(redirect: bool = True):
    if not (os.getenv("ML_CLIENT_ID") and os.getenv("ML_CLIENT_SECRET")):
        raise HTTPException(status_code=400, detail="faltan ML_CLIENT_ID / ML_CLIENT_SECRET en el .env")
    state = secrets.token_urlsafe(16)
    verifier, challenge = _pkce()
    _pending[state] = verifier
    url = MercadoLibreAuth().authorization_url(redirect_uri(), state, challenge)
    return RedirectResponse(url) if redirect else {"url": url, "state": state}


async def _exchange(code: str, state: str | None) -> dict:
    if state is not None and state not in _pending:
        raise HTTPException(status_code=400, detail="state desconocido o vencido: iniciá de nuevo en /ml/login")
    verifier = _pending.pop(state, None) if state is not None else (
        next(reversed(_pending.values()), None) if _pending else None)
    result = await MercadoLibreAuth().exchange_code(code, redirect_uri(), verifier)
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=f"Mercado Libre rechazó el código: {result.get('error')}")
    return result


@router.get("/ml/callback")
async def ml_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code:
        raise HTTPException(status_code=400, detail=f"autorización cancelada o sin código ({error or 'sin code'})")
    return await _exchange(code, state)


@router.post("/ml/exchange")
async def ml_exchange(code: str = Body(..., embed=True), state: str | None = Body(None, embed=True)):
    return await _exchange(code.strip(), state)


@router.get("/ml/status")
async def ml_status():
    return MercadoLibreAuth().status()
