"""External price reference sources for the precio-mercado epic.

Every source is optional and must degrade: a timeout, a 403 or a malformed
payload becomes a ``SourceResult`` with ``available=False`` and a human reason,
never an exception that breaks the analysis. Sources are plain objects with an
async ``search`` method so tests can inject fakes without network access.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

import httpx


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
    kind: str = "externa"  # "interna" | "externa"


@dataclass
class SourceResult:
    source: str
    available: bool
    references: list[PriceReference] = field(default_factory=list)
    reason: str | None = None


class PriceSource(Protocol):
    name: str

    async def search(self, item: str, unit: str | None = None) -> SourceResult: ...


class MercadoLibreSource:
    """Mercado Libre Argentina public search (``/sites/MLA/search``).

    Since 2025 the endpoint answers 403 to anonymous calls. If an
    ``ML_ACCESS_TOKEN`` is present in the environment it is sent as a bearer
    token; otherwise a 403 is reported as "no disponible" and the analysis goes
    on with the remaining sources.
    """

    name = "mercadolibre"
    base_url = "https://api.mercadolibre.com/sites/MLA/search"

    def __init__(self, timeout_s: float = 8.0, limit: int = 20, client: httpx.AsyncClient | None = None):
        self.timeout_s = timeout_s
        self.limit = limit
        self._client = client

    async def search(self, item: str, unit: str | None = None) -> SourceResult:
        headers = {}
        token = os.getenv("ML_ACCESS_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        params = {"q": item, "limit": self.limit, "condition": "new"}
        try:
            if self._client is not None:
                resp = await self._client.get(self.base_url, params=params, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    resp = await client.get(self.base_url, params=params, headers=headers)
        except Exception as exc:  # network errors, timeouts
            return SourceResult(self.name, False, reason=f"no disponible ({type(exc).__name__})")

        if resp.status_code in (401, 403):
            return SourceResult(
                self.name, False,
                reason="no disponible: la API de Mercado Libre exige un token (ML_ACCESS_TOKEN)",
            )
        if resp.status_code != 200:
            return SourceResult(self.name, False, reason=f"no disponible (HTTP {resp.status_code})")

        try:
            results = resp.json().get("results", [])
        except ValueError:
            return SourceResult(self.name, False, reason="no disponible (respuesta inválida)")

        today = date.today().isoformat()
        refs = []
        for r in results:
            price = r.get("price")
            if not isinstance(price, (int, float)) or price <= 0:
                continue
            refs.append(PriceReference(
                source="Mercado Libre",
                description=str(r.get("title", ""))[:200],
                unit_price=float(price),
                observed_on=today,
                url=r.get("permalink"),
                unit="publicación",
            ))
        return SourceResult(self.name, True, references=refs)


def default_external_sources() -> list[PriceSource]:
    """External sources enabled by default.

    No official reference-price source (SIPRO precios testigo, COMPR.AR,
    Compras Públicas Córdoba) exposes a public API reachable without
    credentials, so only Mercado Libre is wired for now.
    """
    return [MercadoLibreSource()]
