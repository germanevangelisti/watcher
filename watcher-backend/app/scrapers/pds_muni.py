"""
PDS-MUNI - Municipal bulletin connector.

First municipality covered: Municipalidad de Cordoba (capital), whose bulletin
lives at https://boletinmunicipal.cordoba.gob.ar.  That site is an Angular SPA
backed by a public, unauthenticated JSON API (``/apibridge/ciudadano/...``):

- ``GET /boletin/dias-publicacion?fechaDesde=..&fechaHasta=..`` lists the days
  with an edition.
- ``GET /boletin?fecha=YYYY-MM-DD`` (or ``?numero=N``) returns the editions of
  that day, each one already segmented into acts (``Publicaciones``) with
  type, number, issuing office, subject (``Asunto``) and a per-act PDF
  (``RutaDocFinal``).

Because the API already segments the edition, there is no LLM segmentation
step: every act becomes one ``analisis`` row and the per-act PDF supplies the
text the monto is read from.

The client is deliberately polite: one request at a time, a fixed delay
between requests, a descriptive User-Agent, and an on-disk cache so a re-run
never downloads the same PDF twice.
"""

from __future__ import annotations

import logging
import re
import time
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .base_scraper import BaseScraper, DocumentType, ScraperConfig, ScraperResult, ScraperType

logger = logging.getLogger(__name__)

CORDOBA_BASE_URL = "https://boletinmunicipal.cordoba.gob.ar"
CORDOBA_API = f"{CORDOBA_BASE_URL}/apibridge/ciudadano"
CORDOBA_MUNICIPIO = "Córdoba"
CORDOBA_ORGANISMO = "Municipalidad de Córdoba"
CORDOBA_FUENTE = "municipal_capital"
USER_AGENT = "WatcherBot/0.1 (+https://github.com/germanevangelisti/watcher; transparencia ciudadana)"

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "boletines" / "municipal" / "cordoba"


# --------------------------------------------------------------------------- #
# Pure parsing (no network): what the tests exercise with fixtures.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MunicipalEdicion:
    numero: int
    fecha: date
    pdf_url: str | None


@dataclass(frozen=True)
class MunicipalActo:
    publicacion_id: int
    edicion: MunicipalEdicion
    tipo_norma: str
    numero: str | None
    reparticion: str | None
    tipo_publicacion: str | None
    asunto: str
    pdf_url: str | None
    fecha_sancion: date | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def tipo_acto(self) -> str:
        """Normalized act type ("Resolución" -> "resolucion")."""
        return _strip_accents(self.tipo_norma).lower().split()[0] if self.tipo_norma else "otro"

    @property
    def numero_acto(self) -> str:
        return f"{self.tipo_norma} N° {self.numero}" if self.numero else self.tipo_norma


def _strip_accents(text: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c)
    )


def _parse_dt(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:19]).date()
    except ValueError:
        return None


def parse_dias(payload: dict[str, Any]) -> list[date]:
    """Publication days out of a ``dias-publicacion`` response."""
    dias = {_parse_dt(x.get("Fecha")) for x in (payload or {}).get("Object") or []}
    return sorted(d for d in dias if d)


def parse_ediciones(payload: dict[str, Any]) -> list[tuple[MunicipalEdicion, list[MunicipalActo]]]:
    """Editions and their acts out of a ``/boletin`` response."""
    result: list[tuple[MunicipalEdicion, list[MunicipalActo]]] = []
    for raw in (payload or {}).get("Object") or []:
        fecha = _parse_dt(raw.get("Fecha"))
        if raw.get("Numero") is None or fecha is None:
            continue
        edicion = MunicipalEdicion(
            numero=int(raw["Numero"]), fecha=fecha, pdf_url=raw.get("RutaDocBoletin")
        )
        actos: list[MunicipalActo] = []
        for tipo_pub in raw.get("TiposPublicacion") or []:
            for tipo_norma in tipo_pub.get("TiposNormas") or []:
                for pub in tipo_norma.get("Publicaciones") or []:
                    if pub.get("Id") is None:
                        continue
                    actos.append(
                        MunicipalActo(
                            publicacion_id=int(pub["Id"]),
                            edicion=edicion,
                            tipo_norma=(pub.get("TipoNorma") or tipo_norma.get("Nombre") or "").strip(),
                            numero=(str(pub.get("NormaNumero") or "").strip() or None),
                            reparticion=(pub.get("Reparticion") or "").strip() or None,
                            tipo_publicacion=pub.get("TipoPublicacion") or tipo_pub.get("Nombre"),
                            asunto=" ".join((pub.get("Asunto") or "").split()),
                            pdf_url=pub.get("RutaDocFinal"),
                            fecha_sancion=_parse_dt(pub.get("FechaSancion")),
                        )
                    )
        result.append((edicion, actos))
    return result


# "$84.421.200,00", "$ 184.800.000.00", "$13.536"
_RE_PESOS = re.compile(r"\$\s*((?:\d{1,3}(?:[.\s]\d{3})+|\d+)(?:[.,]\d{2})?)(?!\d)")


def _to_float(raw: str) -> float | None:
    """Argentine amount string to float: "84.421.200,00", "184.800.000.00", "13.536"."""
    raw = raw.replace(" ", "")
    cents = 0.0
    m = re.match(r"^(.*?)([.,])(\d{2})$", raw)
    # Two trailing digits are cents after a comma, or after a dot when the head
    # already uses dots as thousands separators ("184.800.000.00").
    if m and (m.group(2) == "," or "." in m.group(1)):
        raw, cents = m.group(1), int(m.group(3)) / 100
    try:
        return float(raw.replace(".", "").replace(",", "")) + cents
    except ValueError:
        return None


def extract_monto(text: str, window: int = 8000) -> float | None:
    """The act's headline amount, or ``None``.

    Municipal resolutions repeat the amount they dispose of ("presupuesto
    oficial", "afectación presupuestaria") several times, while incidental
    amounts (insurance minimums, fees) appear once, usually in the annexed
    tender documents.  So: the most repeated ``$`` amount in the opening of
    the text, ties broken by the larger one.
    """
    if not text:
        return None
    values = [v for v in (_to_float(m.group(1)) for m in _RE_PESOS.finditer(text[:window])) if v]
    if not values:
        return None
    counts = Counter(values)
    return max(counts, key=lambda v: (counts[v], v))


# --------------------------------------------------------------------------- #
# Network client
# --------------------------------------------------------------------------- #


class CordobaMunicipalClient:
    """Rate-limited client for the Cordoba municipal bulletin API."""

    def __init__(
        self,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        delay: float = 1.5,
        timeout: float = 60.0,
        http_get: Callable[[str, dict[str, Any] | None], Any] | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.timeout = timeout
        self._http_get = http_get
        self._last = 0.0
        self.requests = 0

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

    def dias_publicacion(self, desde: date, hasta: date) -> list[date]:
        # The SPA sends JS ``Date.toDateString()``; the API also accepts it.
        # ``fechaHasta`` is exclusive on the server side, hence the extra day.
        tope = hasta + timedelta(days=1)
        params = {"fechaDesde": desde.strftime("%a %b %d %Y"), "fechaHasta": tope.strftime("%a %b %d %Y")}
        dias = parse_dias(self._get(f"{CORDOBA_API}/boletin/dias-publicacion", params).json())
        return [d for d in dias if desde <= d <= hasta]

    def ediciones_del_dia(self, dia: date) -> list[tuple[MunicipalEdicion, list[MunicipalActo]]]:
        return parse_ediciones(self._get(f"{CORDOBA_API}/boletin", {"fecha": dia.isoformat()}).json())

    def iter_ediciones(self, desde: date, hasta: date) -> Iterator[tuple[MunicipalEdicion, list[MunicipalActo]]]:
        seen: set[int] = set()
        for dia in self.dias_publicacion(desde, hasta):
            for edicion, actos in self.ediciones_del_dia(dia):
                if edicion.numero in seen:
                    continue
                seen.add(edicion.numero)
                yield edicion, actos

    def acto_pdf_path(self, acto: MunicipalActo) -> Path:
        return self.output_dir / str(acto.edicion.fecha.year) / "actos" / f"pub_{acto.publicacion_id}.pdf"

    def download(self, url: str, dest: Path) -> Path:
        """Download ``url`` into ``dest`` unless it is already cached."""
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = self._get(url)
        tmp = dest.with_suffix(".part")
        tmp.write_bytes(resp.content)
        tmp.replace(dest)
        return dest


def extract_pdf_text(path: Path, max_pages: int = 6) -> str:
    """Text of the first pages of an act PDF (the resolutive part)."""
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages[:max_pages]:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# BaseScraper adapter (keeps the scraper registry contract)
# --------------------------------------------------------------------------- #


class MunicipalScraper(BaseScraper):
    """Downloads Cordoba municipal editions (whole-edition PDFs) by date range."""

    def __init__(self, config: ScraperConfig | None = None, client: CordobaMunicipalClient | None = None):
        if config is None:
            config = ScraperConfig(
                scraper_type=ScraperType.MUNICIPAL,
                base_url=CORDOBA_BASE_URL,
                output_dir=DEFAULT_OUTPUT_DIR,
                rate_limit_delay=1.5,
                skip_weekends=False,
            )
        super().__init__(config)
        self.client = client or CordobaMunicipalClient(
            output_dir=config.output_dir, delay=config.rate_limit_delay
        )

    def get_file_path(self, target_date: date, document_type: DocumentType, **kwargs) -> Path:
        numero = kwargs.get("numero", "x")
        return self.config.output_dir / str(target_date.year) / f"boletin_{target_date:%Y%m%d}_{numero}.pdf"

    def validate_file(self, filepath: Path) -> bool:
        return filepath.exists() and filepath.stat().st_size > 1024

    async def download_single(self, target_date: date, document_type: DocumentType, **kwargs) -> ScraperResult:
        results = await self.download_range(target_date, target_date, document_type)
        if results:
            return results[0]
        return ScraperResult(filename=f"boletin_{target_date:%Y%m%d}.pdf", status="not_available")

    async def download_range(
        self, start_date: date, end_date: date, document_type: DocumentType, **kwargs
    ) -> list[ScraperResult]:
        results: list[ScraperResult] = []
        for edicion, actos in self.client.iter_ediciones(start_date, end_date):
            if not (start_date <= edicion.fecha <= end_date) or not edicion.pdf_url:
                continue
            dest = self.get_file_path(edicion.fecha, document_type, numero=edicion.numero)
            try:
                existed = dest.exists()
                self.client.download(edicion.pdf_url, dest)
                results.append(ScraperResult(
                    filename=dest.name, status="exists" if existed else "downloaded",
                    size=dest.stat().st_size, path=str(dest), url=edicion.pdf_url,
                    metadata={"numero": edicion.numero, "actos": len(actos)},
                ))
            except Exception as exc:  # noqa: BLE001 - reported per file
                results.append(ScraperResult(filename=dest.name, status="error", url=edicion.pdf_url, error=str(exc)))
        return results


def create_municipal_scraper(**kwargs) -> MunicipalScraper:
    """Create a municipal scraper instance."""
    return MunicipalScraper(**kwargs)
