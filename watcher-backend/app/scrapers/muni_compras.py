"""
MuniCompras - Portal de Compras de la Municipalidad de Cordoba (WMU1).

The city bulletin is almost pure regulation: of 509 acts published in 2026, only
two dispose of money.  The city's actual procurement lives in its own portal,
``https://compras.cordoba.gob.ar`` (MuniCompras, launched 2025-03-05), a
Vue/Quasar SPA over a public, unauthenticated JSON API:

- ``GET /apifg/compra/compra?pagina=&cantidad_filas=&fecha_desde=&fecha_hasta=``
  lists the procedures published in the range.  Each item carries the process
  number (``titulo``, e.g. ``2026/000144``), what is bought (``objeto``), the
  process type (``tipo``), the state (``estado``), the file number
  (``expediente``), the issuing body (``entidad`` / ``subentidad`` /
  ``requirente``) and the **official budget** (``presupuesto``).  The envelope
  also carries ``cantidad_paginas``, so paging is bounded.
- ``GET /reporte/reporte/estadisticas/portal`` answers (counts only).

What is *not* public: the awarded supplier and the awarded amount.  The detail
endpoint (``/apifg/compra/compra/{id}``) answers 400 "No se ha proporcionado un
token", ``/tramite/ganador/ganadores_concurso`` answers 500, and the only
document the listing exposes is the offers-opening report (``acta``), not the
award.  So the portal gives the *call* (``presupuesto oficial``), never the
*adjudication*; the ingestion records that gap instead of guessing it.

Like the bulletin connector, this client is deliberately polite: one request at
a time, a fixed delay between them, a descriptive User-Agent and an on-disk
cache keyed by the date range, so a re-run does not hit the API again.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

COMPRAS_BASE_URL = "https://compras.cordoba.gob.ar"
COMPRAS_API = f"{COMPRAS_BASE_URL}/apifg"
COMPRAS_PORTAL_URL = f"{COMPRAS_BASE_URL}/#/compras-publicas/listadocompras/TODOS"
COMPRAS_MUNICIPIO = "Córdoba"
COMPRAS_ORGANISMO = "Municipalidad de Córdoba"
COMPRAS_FUENTE = "municipal_compras"
COMPRAS_NOT_FUENTE = "municipal_capital"  # the bulletin this source is deduped against
USER_AGENT = "WatcherBot/0.1 (+https://github.com/germanevangelisti/watcher; transparencia ciudadana)"

DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / "boletines" / "municipal" / "cordoba" / "compras"
DEFAULT_PAGE_SIZE = 100


# --------------------------------------------------------------------------- #
# Pure parsing (no network): what the tests exercise with fixtures.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CompraPublica:
    """One procedure published in the portal's public listing."""

    id: int
    titulo: str
    objeto: str
    tipo_codigo: str | None
    tipo_nombre: str | None
    estado_codigo: str | None
    estado_nombre: str | None
    entidad: str | None
    subentidad: str | None
    requirente: str | None
    expediente: str | None
    presupuesto: float | None
    fecha_publicacion: date | None
    fecha_creacion: date | None
    numero_llamados: int = 0
    acta: dict[str, Any] | None = None
    # What the listing says about the process itself.  `nombre_compra` is the
    # descriptive name ("SUBASTA ELECTRONICA INVERSA") where `tipo` only carries
    # the short code ("SUBASTA"); the rest dates the call and says whether the
    # process admits extensions, extensions of term and price redetermination.
    nombre_compra: str | None = None
    nombre_compra_codigo: str | None = None
    ultimo_llamado: dict[str, Any] | None = None
    vinculacion_llamado: dict[str, Any] | None = None
    ampliacion: int | None = None
    prorroga: bool | None = None
    redeterminacion: int | None = None

    @property
    def fecha(self) -> date | None:
        """Publication date, falling back to creation: a draft only has the latter."""
        return self.fecha_publicacion or self.fecha_creacion

    @property
    def organismo(self) -> str:
        """Issuing body, as deep as the portal names it."""
        return " - ".join(
            p for p in (COMPRAS_ORGANISMO, self.subentidad or self.entidad) if p
        )


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _parse_fecha(value: Any) -> date | None:
    """``"2026-10-27 16:43:54"`` / ``"2026-10-27T13:34:18.551945"`` -> date."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None


def _parse_monto(value: Any) -> float | None:
    """``presupuesto`` as a float; zero and garbage both mean "not published"."""
    if value is None or value == "":
        return None
    try:
        monto = float(value)
    except (TypeError, ValueError):
        return None
    return monto if monto > 0 else None


def _parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_instancia(raw: Any, descripcion_key: str = "nombre") -> dict[str, Any] | None:
    """Trimmed copy of a ``ultimo_llamado`` / ``vinculacion_llamado`` block."""
    if not isinstance(raw, dict):
        return None
    return {
        "instancia": _clean(raw.get("instancia")),
        "descripcion": _clean(raw.get(descripcion_key)),
        "fecha_desde": _clean(raw.get("fecha_desde")),
        "fecha_hasta": _clean(raw.get("fecha_hasta")),
        "hora_desde": _clean(raw.get("hora_desde")),
        "hora_hasta": _clean(raw.get("hora_hasta")),
    }


def parse_compra(raw: dict[str, Any]) -> CompraPublica | None:
    if raw.get("id") is None:
        return None
    tipo = raw.get("tipo") or {}
    nombre_compra = raw.get("nombre_compra") or {}
    estado = raw.get("estado") or {}
    entidad = raw.get("entidad") or {}
    subentidad = raw.get("subentidad") or {}
    requirente = raw.get("requirente") or {}
    acta = raw.get("acta") or None
    return CompraPublica(
        id=int(raw["id"]),
        titulo=_clean(raw.get("titulo")) or "",
        objeto=_clean(raw.get("objeto")) or "",
        tipo_codigo=_clean(tipo.get("tipo_compra") or nombre_compra.get("nombre_compra")),
        # The descriptive name beats the short code: "SUBASTA ELECTRONICA
        # INVERSA" tells the citizen what the procedure is, "SUBASTA" does not.
        tipo_nombre=_clean(nombre_compra.get("nombre") or tipo.get("nombre")),
        estado_codigo=_clean(estado.get("estado_compra")),
        estado_nombre=_clean(estado.get("nombre")),
        entidad=_clean(entidad.get("nombre")),
        subentidad=_clean(subentidad.get("nombre")),
        requirente=_clean(requirente.get("nombre")),
        expediente=_clean(raw.get("expediente")),
        presupuesto=_parse_monto(raw.get("presupuesto")),
        fecha_publicacion=_parse_fecha(raw.get("fecha_publicacion")),
        fecha_creacion=_parse_fecha(raw.get("fecha_creacion")),
        numero_llamados=int(raw.get("numero_llamados") or 0),
        acta=acta if isinstance(acta, dict) else None,
        nombre_compra=_clean(nombre_compra.get("nombre")),
        nombre_compra_codigo=_clean(nombre_compra.get("nombre_compra")),
        ultimo_llamado=_parse_instancia(raw.get("ultimo_llamado")),
        vinculacion_llamado=_parse_instancia(raw.get("vinculacion_llamado")),
        ampliacion=_parse_int(raw.get("ampliacion")),
        prorroga=bool(raw["prorroga"]) if raw.get("prorroga") is not None else None,
        redeterminacion=_parse_int(raw.get("redeterminacion")),
    )


def parse_compras(payload: dict[str, Any]) -> list[CompraPublica]:
    """Procedures out of one ``/compra/compra`` response."""
    compras = [
        compra
        for compra in (parse_compra(raw) for raw in (payload or {}).get("compras") or [])
        if compra is not None
    ]
    return compras


def parse_cantidad_paginas(payload: dict[str, Any]) -> int:
    try:
        return max(int((payload or {}).get("cantidad_paginas") or 0), 0)
    except (TypeError, ValueError):
        return 0


def portal_url() -> str:
    """Where a person can see the procedure in the portal's own UI."""
    return COMPRAS_PORTAL_URL


# --------------------------------------------------------------------------- #
# Network client
# --------------------------------------------------------------------------- #


class MuniComprasClient:
    """Rate-limited, cached client for the MuniCompras public API."""

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        delay: float = 1.2,
        timeout: float = 60.0,
        http_get: Callable[[str, dict[str, Any] | None], Any] | None = None,
        use_cache: bool = True,
    ):
        self.cache_dir = Path(cache_dir)
        self.delay = delay
        self.timeout = timeout
        self.use_cache = use_cache
        self._http_get = http_get
        self._last = 0.0
        self.requests = 0
        self.cache_hits = 0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last = time.monotonic()

    def _get(self, url: str, params: dict[str, Any] | None = None):
        self._wait()
        self.requests += 1
        if self._http_get is not None:
            return self._http_get(url, params)
        import httpx

        resp = httpx.get(
            url, params=params, timeout=self.timeout,
            headers={"User-Agent": USER_AGENT}, follow_redirects=True,
        )
        resp.raise_for_status()
        return resp

    def _cache_path(self, desde: date, hasta: date, pagina: int, cantidad_filas: int) -> Path:
        return self.cache_dir / f"compras_{desde:%Y%m%d}_{hasta:%Y%m%d}_{cantidad_filas}_{pagina}.json"

    def pagina(self, pagina: int, desde: date, hasta: date, cantidad_filas: int = DEFAULT_PAGE_SIZE) -> dict:
        """One page of the listing, from the cache when it is there."""
        path = self._cache_path(desde, hasta, pagina, cantidad_filas)
        if self.use_cache and path.exists() and path.stat().st_size > 0:
            self.cache_hits += 1
            return json.loads(path.read_text(encoding="utf-8"))
        payload = self._get(
            f"{COMPRAS_API}/compra/compra",
            {
                "pagina": pagina,
                "cantidad_filas": cantidad_filas,
                "fecha_desde": desde.isoformat(),
                "fecha_hasta": hasta.isoformat(),
            },
        ).json()
        if self.use_cache:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def iter_compras(
        self,
        desde: date,
        hasta: date,
        cantidad_filas: int = DEFAULT_PAGE_SIZE,
        max_paginas: int | None = None,
    ) -> Iterator[CompraPublica]:
        """Every procedure in the range, once each, page by page."""
        pagina, total_paginas, seen = 1, None, set()
        while True:
            payload = self.pagina(pagina, desde, hasta, cantidad_filas)
            if total_paginas is None:
                total_paginas = parse_cantidad_paginas(payload)
            compras = parse_compras(payload)
            if not compras:
                break
            for compra in compras:
                if compra.id in seen:
                    continue
                seen.add(compra.id)
                yield compra
            if max_paginas is not None and pagina >= max_paginas:
                break
            if total_paginas is not None and pagina >= total_paginas:
                break
            pagina += 1


# --------------------------------------------------------------------------- #
# Cross-source identifiers (dedupe against the municipal bulletin)
# --------------------------------------------------------------------------- #

# "025522/26", "822-018605/2026", "102-025180/2026  "
_RE_EXPEDIENTE = re.compile(r"\b(\d{1,6}(?:-\d{1,8})?/\d{2,4})\b")
# The same number, but only where the text says it is a file: "Expediente N° …".
_RE_EXPEDIENTE_TEXTO = re.compile(
    r"(?:expediente|expte)\.?[^0-9\n]{0,24}?(\d{1,6}(?:-\d{1,8})?/\d{2,4})",
    re.IGNORECASE,
)
# "Licitación Pública N° 01/26", "Licitación Pública N°001/2026"
_RE_PROCESO = re.compile(
    r"(?:licitaci[oó]n|concurso|subasta|contrataci[oó]n)[^.\n]{0,40}?"
    r"n[°º]?\s*(\d{1,5})\s*/\s*(\d{2,4})",
    re.IGNORECASE,
)


def clave_expediente(raw: str | None) -> str | None:
    """Stable key for a file number, whatever the source's spelling.

    The bulletin writes ``Expediente N° 025522/26`` and the portal writes
    ``102-025180/2026``; both reduce to the *last* numeric group before the year,
    without leading zeros, plus a two-digit year: ``25522/26``.
    """
    if not raw:
        return None
    match = _RE_EXPEDIENTE.search(str(raw))
    if not match:
        return None
    grupos = re.findall(r"\d+", match.group(1))
    if len(grupos) < 2:
        return None
    year, numero = grupos[-1], grupos[-2]
    if len(year) == 4:
        year = year[2:]
    elif len(year) != 2:
        return None
    numero = numero.lstrip("0") or "0"
    return f"{numero}/{year}"


def clave_proceso(numero: str | None, year: str | None) -> tuple[str, str] | None:
    if not numero or not year:
        return None
    if len(year) == 4:
        year = year[2:]
    return (numero.lstrip("0") or "0", year)


def claves_expediente(texto: str | None) -> set[str]:
    """File numbers mentioned in an act's text.

    Only numbers the text introduces as a file number count: the same page also
    carries tender numbers ("Licitación Pública N° 001/2026") that have the same
    ``X/YYYY`` shape, and reading those as files matched unrelated procedures.
    """
    if not texto:
        return set()
    return {k for k in (clave_expediente(m) for m in _RE_EXPEDIENTE_TEXTO.findall(texto)) if k}


def claves_proceso(texto: str | None) -> set[tuple[str, str]]:
    if not texto:
        return set()
    return {
        k
        for k in (clave_proceso(numero, year) for numero, year in _RE_PROCESO.findall(texto))
        if k
    }


# The portal names the procedure ``2026/000144`` (year first), while the bulletin
# writes ``Licitación Pública N° 01/26`` (number first).  Same key, two orders.
_RE_TITULO_PORTAL = re.compile(r"^\s*(\d{4}|\d{2})\s*/\s*(\d{1,6})\s*$")
_RE_TITULO_PORTAL_INV = re.compile(r"^\s*(\d{1,6})\s*/\s*(\d{2}|\d{4})\s*$")


def clave_titulo_portal(titulo: str | None) -> tuple[str, str] | None:
    """``"2026/000144"`` -> ``("144", "26")``; the portal's own procedure number."""
    if not titulo:
        return None
    if (m := _RE_TITULO_PORTAL.match(titulo)):
        return clave_proceso(m.group(2), m.group(1))
    if (m := _RE_TITULO_PORTAL_INV.match(titulo)):
        return clave_proceso(m.group(1), m.group(2))
    return None
