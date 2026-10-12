"""External price reference sources for the precio-mercado epic.

Every source is optional and must degrade: a timeout, a 403 or a malformed
payload becomes a ``SourceResult`` with ``available=False`` and a human reason,
never an exception that breaks the analysis. Sources are plain objects with an
async ``search`` method so tests can inject fakes without network access.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


@dataclass
class PriceReference:
    """One observed price, always with where and when it was observed."""

    source: str
    description: str
    unit_price: float
    observed_on: str  # ISO date
    url: str | None = None
    quantity: float | None = None
    unit: str | None = None
    kind: str = "externa"  # "interna" | "externa" | "oficial"
    process_id: str | None = None  # source-side process id, to exclude the act's own process


@dataclass
class SourceResult:
    source: str
    available: bool
    references: list[PriceReference] = field(default_factory=list)
    reason: str | None = None


class PriceSource(Protocol):
    name: str

    async def search(self, item: str, unit: str | None = None) -> SourceResult: ...


# ---------------------------------------------------------------------------
# Pack normalization
# ---------------------------------------------------------------------------

_PACK_WORDS = r"(?:pack|kit|caja|combo|set|bulto|paquete|blister|lote)"
_COUNT_WORDS = r"(?:unidades|unidad|unid|uds|un|u)"


def unit_stem(unit: str | None) -> str | None:
    """Comparable stem of a unit or item head noun ("Resmas" -> "resma")."""
    from app.services.compras_cba import _norm

    if not unit:
        return None
    words = re.findall(r"[a-z]+", _norm(unit))
    if not words or words[0] in ("unidad", "unidades", "u", "un", "publicacion"):
        return None
    return words[0][:5]


def pack_size(title: str, attributes: list[dict] | None = None, unit: str | None = None) -> int | None:
    """How many units of the act's good one listing sells, when the title or
    the ML attributes say so ("Pack 5 resmas", "caja x 10", "3 unidades",
    UNITS_PER_PACK). Generic: the only product knowledge is the act's own
    unit stem. ``None`` means "one unit, as far as we can tell"."""
    from app.services.compras_cba import _norm

    t = _norm(title)
    candidates: list[int] = []
    stem = unit_stem(unit)
    if stem:
        # "5 resmas", "x5 resmas", "resmas x 5"
        candidates += [int(n) for n in re.findall(rf"\b(?:x\s*)?(\d{{1,4}})\s*(?:x\s*)?{stem}\w*", t)]
        candidates += [int(n) for n in re.findall(rf"\b{stem}\w*\s*x\s*(\d{{1,4}})\b", t)]
    if not candidates:
        candidates += [int(n) for n in re.findall(rf"\b{_PACK_WORDS}\s*(?:de|x|por)?\s*(\d{{1,4}})\b(?!\s*(?:g|gr|grs|kg|ml|cc|l|lt|mm|cm|m|hojas)\b)", t)]
        candidates += [int(n) for n in re.findall(rf"\b(?:x\s*)?(\d{{1,4}})\s*{_COUNT_WORDS}\b", t)]
    if not candidates:
        for a in attributes or []:
            aid = str(a.get("id", "")).upper()
            if aid in ("UNITS_PER_PACK", "UNITS_PER_PACKAGE", "PACKAGE_UNITS", "SALE_FORMAT", "UNITS_PER_SALE"):
                m = re.search(r"\d+", str(a.get("value_name") or ""))
                if m:
                    candidates.append(int(m.group()))
    candidates = [c for c in candidates if 2 <= c <= 1000]
    return max(candidates) if candidates else None


def listing_reference(title: str, price: float, url: str | None, unit: str | None,
                      attributes: list[dict] | None = None, note: str = "") -> PriceReference:
    """A Mercado Libre price normalized to the act's unit."""
    n = pack_size(title, attributes, unit)
    desc = title[:170] + (note or "")
    if n:
        desc += f" (pack de {n}: precio ÷ {n})"
    return PriceReference(
        source="Mercado Libre",
        description=desc[:240],
        unit_price=float(price) / (n or 1),
        observed_on=date.today().isoformat(),
        url=url,
        quantity=float(n) if n else None,
        unit=(unit or "unidad"),
    )


ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ML_TOKEN_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "ml_token.json"


class MercadoLibreAuth:
    """Access token for the Mercado Libre API, refreshed automatically.

    Order: ``ML_ACCESS_TOKEN`` (fixed, as is) -> cached token while valid ->
    ``refresh_token`` grant when a refresh token is known (cache or
    ``ML_REFRESH_TOKEN``) -> ``client_credentials`` grant with
    ``ML_CLIENT_ID`` / ``ML_CLIENT_SECRET``. Refresh tokens are single use, so
    the newest one is kept in ``.cache/ml_token.json`` (gitignored), never in
    the ``.env``. Secrets are never logged.
    """

    def __init__(self, cache_path: Path = ML_TOKEN_CACHE, client: httpx.AsyncClient | None = None,
                 clock=time.time):
        self.cache_path = cache_path
        self._client = client
        self._clock = clock
        self._memory: dict | None = None

    @staticmethod
    def configured() -> bool:
        return bool(os.getenv("ML_ACCESS_TOKEN") or (os.getenv("ML_CLIENT_ID") and os.getenv("ML_CLIENT_SECRET")))

    def _load(self) -> dict:
        if self._memory is not None:
            return self._memory
        try:
            self._memory = json.loads(self.cache_path.read_text("utf-8"))
        except (OSError, ValueError):
            self._memory = {}
        return self._memory

    def _save(self, data: dict) -> None:
        self._memory = data
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(data), "utf-8")
        except OSError as exc:
            logger.warning("mercadolibre: could not persist token cache (%s)", type(exc).__name__)

    def invalidate(self) -> None:
        data = dict(self._load())
        data.pop("access_token", None)
        self._save(data)

    AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"

    def authorization_url(self, redirect_uri: str, state: str, code_challenge: str | None = None) -> str:
        from urllib.parse import urlencode

        q = {"response_type": "code", "client_id": os.getenv("ML_CLIENT_ID", ""),
             "redirect_uri": redirect_uri, "state": state}
        if code_challenge:
            q.update({"code_challenge": code_challenge, "code_challenge_method": "S256"})
        return f"{self.AUTH_URL}?{urlencode(q)}"

    def status(self) -> dict:
        """Token state without any secret value."""
        c = self._load()
        return {"configurado": self.configured(), "token_de_usuario": bool(c.get("user") and c.get("refresh_token")),
                "usuario_id": c.get("user_id"),
                "expira_en_s": max(0, int(c.get("expires_at", 0) - self._clock())) if c.get("access_token") else 0}

    async def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> dict:
        """authorization_code grant: stores the user access + refresh token in
        the gitignored cache. Returns a secret-free summary."""
        client_id, secret = os.getenv("ML_CLIENT_ID"), os.getenv("ML_CLIENT_SECRET")
        if not (client_id and secret):
            return {"ok": False, "error": "faltan ML_CLIENT_ID / ML_CLIENT_SECRET"}
        form = {"grant_type": "authorization_code", "client_id": client_id, "client_secret": secret,
                "code": code, "redirect_uri": redirect_uri}
        if code_verifier:
            form["code_verifier"] = code_verifier
        try:
            if self._client is not None:
                resp = await self._client.post(ML_TOKEN_URL, data=form, headers={"accept": "application/json"})
            else:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(ML_TOKEN_URL, data=form, headers={"accept": "application/json"})
        except Exception as exc:
            return {"ok": False, "error": f"no disponible ({type(exc).__name__})"}
        if resp.status_code != 200:
            try:
                err = resp.json().get("error") or resp.json().get("message")
            except ValueError:
                err = None
            return {"ok": False, "error": f"HTTP {resp.status_code}" + (f": {err}" if err else "")}
        body = resp.json()
        self._save({
            "access_token": body.get("access_token"),
            "expires_at": self._clock() + float(body.get("expires_in", 21600)),
            "refresh_token": body.get("refresh_token"),
            "user": True,
            "user_id": body.get("user_id"),
        })
        return {"ok": True, "usuario_id": body.get("user_id"), "refresh_token_guardado": bool(body.get("refresh_token"))}

    async def token(self) -> str | None:
        fixed = os.getenv("ML_ACCESS_TOKEN")
        if fixed:
            return fixed
        client_id, secret = os.getenv("ML_CLIENT_ID"), os.getenv("ML_CLIENT_SECRET")
        if not (client_id and secret):
            return None
        cached = self._load()
        if cached.get("access_token") and cached.get("expires_at", 0) > self._clock() + 60:
            return cached["access_token"]
        refresh = cached.get("refresh_token") or os.getenv("ML_REFRESH_TOKEN")
        form = {"client_id": client_id, "client_secret": secret}
        form.update({"grant_type": "refresh_token", "refresh_token": refresh} if refresh
                    else {"grant_type": "client_credentials"})
        try:
            if self._client is not None:
                resp = await self._client.post(ML_TOKEN_URL, data=form, headers={"accept": "application/json"})
            else:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(ML_TOKEN_URL, data=form, headers={"accept": "application/json"})
        except Exception as exc:
            logger.warning("mercadolibre: token request failed (%s)", type(exc).__name__)
            return None
        if resp.status_code != 200:
            logger.warning("mercadolibre: token grant %s rejected (HTTP %s)", form["grant_type"], resp.status_code)
            if refresh and cached.get("refresh_token"):
                self._save({})  # a stale rotated refresh token: next call retries from scratch
            return None
        body = resp.json()
        self._save({
            "access_token": body.get("access_token"),
            "expires_at": self._clock() + float(body.get("expires_in", 21600)),
            "refresh_token": body.get("refresh_token") or refresh,
            "user": bool(refresh) and bool(cached.get("user") or os.getenv("ML_REFRESH_TOKEN")),
            "user_id": cached.get("user_id"),
        })
        return body.get("access_token")


class MercadoLibreSource:
    """Mercado Libre Argentina public search (``/sites/MLA/search``).

    Since 2025 the endpoint answers 403 to anonymous calls. If an
    ``ML_ACCESS_TOKEN`` is present in the environment it is sent as a bearer
    token; otherwise a 403 is reported as "no disponible" and the analysis goes
    on with the remaining sources.
    """

    name = "mercadolibre"
    base_url = "https://api.mercadolibre.com/sites/MLA/search"

    def __init__(self, timeout_s: float = 8.0, limit: int = 20, client: httpx.AsyncClient | None = None,
                 auth: MercadoLibreAuth | None = None):
        self.timeout_s = timeout_s
        self.limit = limit
        self._client = client
        self.auth = auth or MercadoLibreAuth(client=client)

    catalog_url = "https://api.mercadolibre.com/products/search"
    product_items_url = "https://api.mercadolibre.com/products/{id}/items"
    max_products = 5

    async def _get(self, params: dict, headers: dict, url: str | None = None) -> httpx.Response:
        url = url or self.base_url
        if self._client is not None:
            return await self._client.get(url, params=params, headers=headers)
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            return await client.get(url, params=params, headers=headers)

    @staticmethod
    def _stems(text: str) -> list[str]:
        from app.services.compras_cba import _norm
        return [w[:5] for w in re.findall(r"[a-z0-9]+", _norm(text)) if len(w) >= 3 or (len(w) == 2 and any(ch.isdigit() for ch in w))]

    async def _catalog_search(self, item: str, headers: dict, unit: str | None = None) -> SourceResult:
        """Fallback for app tokens: ``/sites/MLA/search`` is forbidden to
        client_credentials tokens, but the catalog (``/products/search``) and
        each product's active listings (``/products/{id}/items``) are not."""
        try:
            resp = await self._get({"status": "active", "site_id": "MLA", "q": item, "limit": 20},
                                   headers, self.catalog_url)
        except Exception as exc:
            return SourceResult(self.name, False, reason=f"no disponible ({type(exc).__name__})")
        if resp.status_code != 200:
            return SourceResult(self.name, False, reason=f"no disponible (catálogo HTTP {resp.status_code})")
        try:
            products = resp.json().get("results", [])
        except ValueError:
            return SourceResult(self.name, False, reason="no disponible (respuesta inválida)")
        stop = {"del", "los", "las", "con", "para", "sin", "por", "una", "uno", "unos", "unas"}
        wanted = [w for w in self._stems(item) if w not in stop][:2]
        # A short model/size token with a digit ("A4", "R16") separates
        # variants that share the noun ("resmas A4" vs "resmas oficio").
        from app.services.compras_cba import _norm
        digit = next((w for w in re.findall(r"[a-z0-9]+", _norm(item)) if re.search(r"\d", w) and re.search(r"[a-z]", w)), None)
        if digit and digit[:5] not in wanted:
            wanted.append(digit[:5])
        refs: list[PriceReference] = []
        for prod in products:
            if len(refs) >= self.max_products:
                break
            name = str(prod.get("name", ""))
            name_stems = self._stems(name)
            have = set(name_stems)
            head = next((w for w in name_stems if not w.isdigit() and w not in {"pack", "kit", "combo", "set", "x"}), "")
            # The searched good must be the product's head noun, not an
            # accessory ("Sellador de neumáticos", "Pillow top para colchones").
            if wanted and (not all(w in have for w in wanted) or head != wanted[0]):
                continue  # catalog search is loose ("resma" matches printer combos)
            try:
                ir = await self._get({}, headers, self.product_items_url.format(id=prod.get("id")))
                items = ir.json().get("results", []) if ir.status_code == 200 else []
            except Exception:
                continue
            prices = sorted(float(i["price"]) for i in items
                            if isinstance(i.get("price"), (int, float)) and i["price"] > 0
                            and i.get("currency_id", "ARS") == "ARS")
            if not prices:
                continue
            refs.append(listing_reference(
                name, prices[len(prices) // 2], f"https://www.mercadolibre.com.ar/p/{prod.get('id')}",
                unit or item, prod.get("attributes"), f" (mediana de {len(prices)} publicaciones)"))
        return SourceResult(self.name, True, references=refs)

    async def search(self, item: str, unit: str | None = None) -> SourceResult:
        params = {"q": item, "limit": self.limit, "condition": "new"}
        resp = None
        for attempt in range(2):
            headers = {}
            token = await self.auth.token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
            try:
                resp = await self._get(params, headers)
            except Exception as exc:  # network errors, timeouts
                return SourceResult(self.name, False, reason=f"no disponible ({type(exc).__name__})")
            if resp.status_code == 401 and token and attempt == 0:
                self.auth.invalidate()  # expired or revoked: refresh once and retry
                continue
            break

        if resp.status_code == 403 and headers.get("Authorization"):
            return await self._catalog_search(item, headers, unit)
        if resp.status_code in (401, 403):
            reason = ("no disponible: la API de Mercado Libre rechazó el token configurado"
                      if MercadoLibreAuth.configured()
                      else "no disponible: la API de Mercado Libre exige credenciales (ML_CLIENT_ID / ML_CLIENT_SECRET)")
            return SourceResult(self.name, False, reason=reason)
        if resp.status_code != 200:
            return SourceResult(self.name, False, reason=f"no disponible (HTTP {resp.status_code})")

        try:
            results = resp.json().get("results", [])
        except ValueError:
            return SourceResult(self.name, False, reason="no disponible (respuesta inválida)")

        refs = []
        for r in results:
            price = r.get("price")
            if not isinstance(price, (int, float)) or price <= 0:
                continue
            refs.append(listing_reference(str(r.get("title", "")), price, r.get("permalink"),
                                          unit or item, r.get("attributes")))
        return SourceResult(self.name, True, references=refs)


class ComprasCbaReferenceSource:
    """Official reference prices: renglones of finalized ComprasCba processes.

    Each renglón of an electronic process carries the "precio de referencia"
    the buying agency estimated per unit. It is an official estimate, not a
    market quote, and it is labelled as such.
    """

    name = "compras_cba_referencias"

    def __init__(self, procesos_loader):
        # ``procesos_loader`` is an async callable returning ``list[Proceso]``
        # (cached by the service); injected so tests need no network.
        self._load = procesos_loader

    async def search(self, item: str, unit: str | None = None) -> SourceResult:
        from app.services.compras_cba import PORTAL_HISTORICO, _norm

        try:
            procesos = await self._load()
        except Exception as exc:
            return SourceResult(self.name, False, reason=f"no disponible ({type(exc).__name__})")
        words = [w for w in re.findall(r"[a-z]{4,}", _norm(item)) if w not in ("para", "destino", "con")][:2]
        if not words:
            return SourceResult(self.name, True, reason="ítem sin palabras clave")
        # Every key word must appear ("aceite de soja" is not "aceite de girasol").
        stems = [w.rstrip("s") for w in words]
        refs = []
        for p in procesos:
            for r in p.renglones:
                desc = _norm(r.descripcion)
                if r.precio_referencia and all(s in desc for s in stems):
                    observed = p.fecha_limite or ""
                    if len(observed) >= 10 and observed[2] == "/":
                        observed = f"{observed[6:10]}-{observed[3:5]}-{observed[0:2]}"
                    refs.append(PriceReference(
                        source=f"ComprasCba - precio de referencia oficial ({p.servicio})",
                        description=f"{p.nro}: {r.descripcion}"[:200],
                        unit_price=r.precio_referencia,
                        observed_on=observed,
                        url=PORTAL_HISTORICO,
                        quantity=r.cantidad,
                        kind="oficial",
                        process_id=p.nro,
                    ))
        return SourceResult(self.name, True, references=refs[:30],
                            reason=None if refs else "ningún renglón de referencia coincide")


def default_external_sources() -> list[PriceSource]:
    """External sources that need no database: Mercado Libre.

    The ComprasCba reference source needs the cached portal grid and is built
    by the service (see ``precio_mercado_service.analyze``).
    """
    return [MercadoLibreSource()]
