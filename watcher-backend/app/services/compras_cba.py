"""ComprasCba (Portal de Compras Públicas de Córdoba) adapter.

The public portal (``webecommerce.cba.gov.ar/VistaPublica``) is an ASP.NET
WebForms app with no API. Without credentials it exposes:

- a search grid (activas / finalizadas) filterable by "fecha límite" range,
  whose rows carry the process number, type, administrative unit, object,
  and either the renglones (description, quantity, reference price, official
  budget) - electronic processes - or just object + official budget -
  presencial processes;
- a detail page per process with downloadable attachments (pliego, actas).

This module finds the process of a boletín act (official budget == act amount,
then object similarity), returns its renglones and, when the grid has none,
parses the quantities out of the pliego PDF. Everything degrades: any failure
returns ``found=False`` with a reason. The HTTP layer is injectable
(``fetcher``) so tests run against saved HTML/PDF fixtures without network.
"""

from __future__ import annotations

import asyncio
import html as htmllib
import io
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Protocol

logger = logging.getLogger(__name__)

PORTAL = "https://webecommerce.cba.gov.ar/VistaPublica/OportunidadProveedores.aspx"
PORTAL_HISTORICO = PORTAL + "?ver=historico"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Renglon:
    numero: int | None
    descripcion: str
    cantidad: float | None
    precio_referencia: float | None = None
    presupuesto: float | None = None


@dataclass
class Proceso:
    nro: str
    tipo: str
    servicio: str
    objeto: str
    fecha_limite: str | None
    estado: str
    presupuesto_total: float | None
    renglones: list[Renglon] = field(default_factory=list)
    row_control: str | None = None  # "gv$ctlNN" for the detail postback
    finalizada: bool = True


@dataclass
class ProcesoMatch:
    found: bool
    reason: str | None = None
    proceso: Proceso | None = None
    renglones_origen: str | None = None  # "grilla" | "pliego"
    documento: str | None = None
    portal_url: str = PORTAL_HISTORICO

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ProcesoMatch:
        p = d.get("proceso")
        proceso = None
        if p:
            p = dict(p)
            p["renglones"] = [Renglon(**r) for r in p.get("renglones", [])]
            proceso = Proceso(**p)
        return cls(found=d["found"], reason=d.get("reason"), proceso=proceso,
                   renglones_origen=d.get("renglones_origen"), documento=d.get("documento"),
                   portal_url=d.get("portal_url", PORTAL_HISTORICO))


# ---------------------------------------------------------------------------
# Parsing helpers (pure, unit-tested against fixtures)
# ---------------------------------------------------------------------------


def _norm(text: str | None) -> str:
    return unicodedata.normalize("NFKD", (text or "").lower()).encode("ascii", "ignore").decode()


def parse_money(text: str | None) -> float | None:
    """``"$ 186.031.008,0000"`` -> 186031008.0"""
    if not text:
        return None
    t = re.sub(r"<[^>]+>", "", text)
    t = re.sub(r"[^\d,.]", "", t)
    if not t:
        return None
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def parse_qty(text: str | None) -> float | None:
    if not text:
        return None
    t = re.sub(r"[^\d,.]", "", text)
    if not t:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    t = t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v > 0 else None


def _cells(row_html: str) -> list[str]:
    return re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.S)


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", cell))).strip()


def parse_form(page: str) -> dict[str, str]:
    """All form fields with their current values (hidden, text, selects)."""
    data = dict(re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page))
    for name, value in re.findall(r'<input[^>]*type="text"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page):
        data.setdefault(name, value)
    for name in re.findall(r'<select[^>]*name="([^"]+)"', page):
        m = re.search(rf'<select[^>]*name="{re.escape(name)}"[^>]*>(.*?)</select>', page, re.S)
        if not m:
            continue
        sel = (re.search(r'<option[^>]*selected="selected"[^>]*value="([^"]*)"', m.group(1))
               or re.search(r'<option[^>]*value="([^"]*)"', m.group(1)))
        data[name] = sel.group(1) if sel else ""
    return {k: htmllib.unescape(v) for k, v in data.items()}


def parse_grid(page: str, finalizada: bool = True) -> list[Proceso]:
    """Rows of the search grid, each with its renglones when the grid has them."""
    start = page.find('id="gv"')
    if start < 0:
        return []
    grid = page[start:]
    parts = re.split(r'<tr class="(?:Renglon|RenglonAlternativo)">', grid)[1:]
    procesos: list[Proceso] = []
    for part in parts:
        cells = _cells(part)
        if len(cells) < 8:
            continue
        objeto_m = re.search(r'title="([^"]*)"', part)
        objeto = htmllib.unescape(objeto_m.group(1)) if objeto_m else _text(cells[3])
        control = re.search(r'name="(gv\$ctl\d+)\$btnVerDetalles"', part)
        items = re.search(r'id="gv_btnItems_\d+_gv"[^>]*>(.*?)</table>', part, flags=re.S)
        renglones: list[Renglon] = []
        total = None
        if items:
            header = " ".join(_text(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", items.group(1), re.S))
            rows = re.findall(r"<tr>\s*(<td.*?)</tr>", items.group(1), flags=re.S)
            if "Cantidad" in header:
                for i, row in enumerate(rows, start=1):
                    c = _cells(row)
                    if len(c) >= 4:
                        renglones.append(Renglon(i, _text(c[0]), parse_qty(_text(c[1])),
                                                 parse_money(c[2]), parse_money(c[3])))
                total = sum(r.presupuesto or 0 for r in renglones) or None
            elif rows:
                c = _cells(rows[0])
                if len(c) >= 2:
                    total = parse_money(c[1])
        procesos.append(Proceso(
            nro=_text(cells[0]), tipo=_text(cells[1]), servicio=_text(cells[2]), objeto=objeto,
            fecha_limite=_text(cells[5]) or None, estado=_text(cells[6]), presupuesto_total=total,
            renglones=renglones, row_control=control.group(1) if control else None, finalizada=finalizada,
        ))
    return procesos


_ROW_RE = re.compile(r"^\s{0,20}0?(\d{1,3})\s{2,}(?:(\S.*?)\s{2,})?(\d{1,3}(?:\.\d{3})+|\d+)(?:\s{2,}.*)?\s*$")
_BOILER = re.compile(r"seg[uú]n pliegos? de|especificaciones t[eé]cnicas\.?", re.I)


def parse_pliego_renglones(text: str) -> list[Renglon]:
    """Renglón / descripción / cantidad from the pliego's layout text.

    Pliegos lay the table out as ``<n>   <desc?>   <qty>`` with the description
    wrapped on the lines above and below. Only the first table is read.
    """
    lines = text.splitlines()
    header = next((i for i, ln in enumerate(lines) if re.search(r"\bcant(idad|\.)", ln, re.I)), None)
    if header is None:
        return []
    rows: list[tuple[int, re.Match]] = []
    for i in range(header + 1, min(len(lines), header + 120)):
        m = _ROW_RE.match(lines[i])
        if m:
            n = int(m.group(1))
            if rows and n <= int(rows[-1][1].group(1)):
                break  # numbering restarts: a second table
            rows.append((i, m))
        elif rows and i - rows[-1][0] > 6:
            break
    out: list[Renglon] = []
    prev_end = header
    for k, (i, m) in enumerate(rows):
        nxt = rows[k + 1][0] if k + 1 < len(rows) else i + 6
        above = [ln.strip() for ln in lines[prev_end + 1:i] if ln.strip()]
        below: list[str] = []
        for ln in lines[i + 1:nxt]:
            s = ln.strip()
            if not s or re.match(r"(?i)nota|art", s):
                break
            below.append(s)
            if s.endswith("."):
                break
        desc = " ".join(above[-1:] + ([m.group(2)] if m.group(2) else []) + below)
        desc = re.sub(r"\s+", " ", _BOILER.sub("", desc)).strip(" .")
        out.append(Renglon(int(m.group(1)), desc, parse_qty(m.group(3))))
        prev_end = i + len(below)
    return out


def pdf_text(content: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:  # pragma: no cover - optional dependency
        return ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join((p.extract_text(layout=True) or "") for p in pdf.pages[:15])


_GENERIC = frozenset({
    "adquisicion", "adquirir", "compra", "para", "destino", "destinados", "destinadas", "licitacion",
    "publica", "seleccion", "concurso", "precios", "provision", "contratacion", "esta", "reparticion",
    "electronica", "subasta", "inversa", "segun", "pliego", "pliegos", "varios", "varias",
    # number words: quantities are matched separately, never as object
    "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "veinte", "treinta",
    "cuarenta", "cincuenta", "cien", "ciento", "doscientos", "trescientos", "cuatrocientos",
    "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos", "miles", "millon",
})


def object_similarity(a: str, b: str) -> float:
    ta = {t for t in re.findall(r"[a-z]{4,}", _norm(a))} - _GENERIC
    tb = {t for t in re.findall(r"[a-z]{4,}", _norm(b))} - _GENERIC
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _shared(a: str, b: str) -> int:
    ta = {t for t in re.findall(r"[a-z]{4,}", _norm(a))} - _GENERIC
    tb = {t for t in re.findall(r"[a-z]{4,}", _norm(b))} - _GENERIC
    return len(ta & tb)


def match_proceso(procesos: list[Proceso], monto: float | None, concepto: str | None,
                  cantidad_hint: float | None = None) -> Proceso | None:
    """Official budget equal to the act amount wins; then a renglón with the
    quantity the act states plus a related object; then a strong object match."""
    if monto:
        # Amount alone is not enough: boletín acts sometimes carry another act's
        # amount (a mis-parse upstream), so the object must share a word too.
        by_amount = [p for p in procesos
                     if p.presupuesto_total and abs(p.presupuesto_total - monto) <= max(1.0, monto * 0.001)
                     and _shared(p.objeto + " " + " ".join(r.descripcion for r in p.renglones), concepto or "") >= 1]
        if by_amount:
            return max(by_amount, key=lambda p: object_similarity(p.objeto, concepto or ""))
    if cantidad_hint:
        by_qty = [p for p in procesos
                  if any(r.cantidad == cantidad_hint for r in p.renglones)
                  and object_similarity(p.objeto + " " + " ".join(r.descripcion for r in p.renglones), concepto or "") >= 0.5]
        if by_qty:
            return by_qty[0]
    scored = sorted(((object_similarity(p.objeto, concepto or ""), p) for p in procesos), key=lambda x: -x[0])
    # Object alone is weak (many processes buy "colchones"): demand a strong
    # overlap on at least two meaningful words and a single best candidate.
    if (scored and scored[0][0] >= 0.8 and _shared(scored[0][1].objeto, concepto or "") >= 2
            and (len(scored) == 1 or scored[1][0] < scored[0][0])):
        return scored[0][1]
    return None


# ---------------------------------------------------------------------------
# HTTP layer (injectable)
# ---------------------------------------------------------------------------


class Fetcher(Protocol):
    async def search(self, desde: date, hasta: date, finalizadas: bool) -> str: ...

    async def pliego(self, proceso: Proceso, desde: date, hasta: date) -> tuple[str | None, bytes | None]: ...


class PortalFetcher:
    """Talks to the real portal. One session per call; never needs credentials."""

    def __init__(self, timeout_s: float = 60.0):
        self.timeout_s = timeout_s

    def _filters(self, desde: date, hasta: date, finalizadas: bool) -> dict[str, str]:
        f = {"ddlMostrar": "99999"}
        if finalizadas:
            f["Atajos"] = "rdbtHistorico"
        for name, d in (("txtFecha_Desde_Limite", desde), ("txtFecha_Hasta_Limite", hasta)):
            f.update({name: d.strftime("%d/%m/%Y"), f"{name}_hidDia": str(d.day),
                      f"{name}_hidMes": str(d.month), f"{name}_hidAno": str(d.year)})
        return f

    async def _grid(self, client, desde: date, hasta: date, finalizadas: bool) -> tuple[str, str]:
        url = PORTAL_HISTORICO if finalizadas else PORTAL
        first = await client.get(url)
        data = parse_form(first.text)
        data.update(self._filters(desde, hasta, finalizadas))
        data["btnBuscar"] = "Buscar"
        resp = await client.post(url, data=data)
        return url, resp.text

    async def search(self, desde: date, hasta: date, finalizadas: bool) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (Watcher)"}) as client:
            return (await self._grid(client, desde, hasta, finalizadas))[1]

    async def pliego(self, proceso: Proceso, desde: date, hasta: date) -> tuple[str | None, bytes | None]:
        import httpx

        if not proceso.row_control:
            return None, None
        async with httpx.AsyncClient(timeout=self.timeout_s, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (Watcher)"}) as client:
            url, grid = await self._grid(client, desde, hasta, proceso.finalizada)
            data = parse_form(grid)
            data.update(self._filters(desde, hasta, proceso.finalizada))
            data[f"{proceso.row_control}$btnVerDetalles.x"] = "5"
            data[f"{proceso.row_control}$btnVerDetalles.y"] = "5"
            detail = await client.post(url, data=data)
            docs = re.findall(r"<td>([^<]+\.pdf)</td>.*?name=\"(GvDocAdj\$ctl\d+\$btnDetalles)\"", detail.text, flags=re.S | re.I)
            pick = next(((n, c) for n, c in docs if "pliego" in n.lower()), None)
            if not pick:
                return None, None
            form = parse_form(detail.text)
            form[f"{pick[1]}.x"] = "5"
            form[f"{pick[1]}.y"] = "5"
            pdf = await client.post(str(detail.url), data=form)
            if not pdf.content.startswith(b"%PDF"):
                return pick[0], None
            return htmllib.unescape(pick[0]), pdf.content


# ---------------------------------------------------------------------------
# Source
# ---------------------------------------------------------------------------


class ComprasCbaSource:
    name = "compras_cba"

    def __init__(self, fetcher: Fetcher | None = None):
        self.fetcher = fetcher or PortalFetcher()

    @staticmethod
    def window(fecha: date | None) -> tuple[date, date]:
        f = fecha or date.today()
        return f - timedelta(days=60), f + timedelta(days=75)

    async def find(self, fecha: date | None, monto: float | None, concepto: str | None,
                   cantidad_hint: float | None = None) -> ProcesoMatch:
        desde, hasta = self.window(fecha)
        try:
            pages = await asyncio.gather(self.fetcher.search(desde, hasta, True),
                                         self.fetcher.search(desde, hasta, False))
        except Exception as exc:
            return ProcesoMatch(False, reason=f"portal no disponible ({type(exc).__name__})")
        procesos = parse_grid(pages[0], True) + parse_grid(pages[1], False)
        if not procesos:
            return ProcesoMatch(False, reason="el portal no devolvió procesos para esas fechas")
        proceso = match_proceso(procesos, monto, concepto, cantidad_hint)
        if proceso is None:
            return ProcesoMatch(False, reason=f"ningún proceso coincide en monto u objeto ({len(procesos)} revisados)")
        if proceso.renglones and any(r.cantidad for r in proceso.renglones):
            return ProcesoMatch(True, proceso=proceso, renglones_origen="grilla")
        try:
            doc, content = await self.fetcher.pliego(proceso, desde, hasta)
        except Exception as exc:
            return ProcesoMatch(True, reason=f"proceso encontrado; pliego no disponible ({type(exc).__name__})", proceso=proceso)
        if not content:
            return ProcesoMatch(True, reason="proceso encontrado; sin pliego descargable", proceso=proceso, documento=doc)
        text = await asyncio.to_thread(pdf_text, content)
        renglones = parse_pliego_renglones(text)
        if not renglones:
            return ProcesoMatch(True, reason="proceso encontrado; el pliego no tiene una tabla de renglones legible",
                                proceso=proceso, documento=doc)
        proceso.renglones = renglones
        return ProcesoMatch(True, proceso=proceso, renglones_origen="pliego", documento=doc)

    async def reference_renglones(self, fecha: date | None, days: int = 365) -> list[Proceso]:
        """Finalized processes of the last year whose grid carries reference prices."""
        hasta = (fecha or date.today()) + timedelta(days=75)
        desde = hasta - timedelta(days=days)
        try:
            page = await self.fetcher.search(desde, hasta, True)
        except Exception as exc:
            logger.warning("compras_cba: reference search failed: %s", exc)
            return []
        return [p for p in parse_grid(page, True) if any(r.precio_referencia for r in p.renglones)]
