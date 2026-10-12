"""Precio de mercado: detect observable purchases and compare unit prices.

Flow (always triggered by the user, one act at a time):

1. ``list_observables`` - heuristic over ``ejecucion_presupuestaria``: purchase
   acts (licitación / compra directa) of standardizable goods with an amount.
2. ``analyze`` - extract item / quantity / unit / amount (LLM via
   ``llm_provider``, regex fallback), gather internal references (similar acts
   in the corpus) and external ones (``price_sources``), and compare the unit
   price against the median.

The output never contains a verdict: only numbers, sources and dates plus a
classification driven by configurable thresholds.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import date

from app.db.models import Analisis, Boletin, EjecucionPresupuestaria, FuenteExternaCache
from app.services.compras_cba import ComprasCbaSource, Proceso, ProcesoMatch, Renglon
from app.services.fts_service import _FTS5_STOPWORDS, _sin_acentos
from app.services.price_sources import (
    ComprasCbaReferenceSource,
    PriceReference,
    PriceSource,
    SourceResult,
    default_external_sources,
)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class Thresholds:
    observable: float = 0.30
    alerta: float = 1.00
    min_references: int = 3

    @classmethod
    def from_env(cls) -> Thresholds:
        def _f(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, default))
            except ValueError:
                return default

        return cls(
            observable=_f("PRECIO_MERCADO_UMBRAL_OBSERVABLE", 0.30),
            alerta=_f("PRECIO_MERCADO_UMBRAL_ALERTA", 1.00),
            min_references=int(_f("PRECIO_MERCADO_MIN_REFERENCIAS", 3)),
        )


PURCHASE_TYPES = ("licitacion", "compra", "compra_directa", "contratacion_directa", "concurso_precios")

# Standardizable goods: things with a recognizable market price per unit.
GOODS_KEYWORDS = (
    "resma", "papel", "libros de actas", "toner", "cartucho", "aceite", "azucar", "harina",
    "leche", "yerba", "alimento", "mercaderia", "luminaria", "lampara", "led", "cable",
    "conector", "computadora", "notebook", "equipos informaticos", "impresora", "monitor",
    "mueble", "mobiliario", "silla", "escritorio", "neumatico", "cubierta", "combustible",
    "nafta", "gasoil", "medicamento", "insumos", "guantes", "barbijo", "epp", "uniforme",
    "indumentaria", "calzado", "colchon", "frazada", "vehiculo", "camioneta", "trailer",
    "descargador", "transformador", "medidor", "carne", "pollo", "extintor", "bateria", "filtro",
)

# Not standardizable (services, works, rentals): excluded even if "adquisición".
EXCLUDE_KEYWORDS = (
    "obra", "construccion", "servicio", "mantenimiento", "alquiler", "locacion",
    "consultoria", "limpieza", "vigilancia", "seguridad privada", "transporte de",
    "subsidio", "refaccion", "reparacion", "deuda", "fideicomiso", "venta", "subasta",
    "auditoria", "mejoramiento", "concesion", "interconexion", "ampliacion",
)

PURCHASE_VERBS = ("adquisicion", "adquirir", "compra", "provision", "suministro")

UNIT_WORDS = (
    "unidades", "unidad", "u", "resmas", "resma", "litros", "litro", "lts", "kg", "kilos",
    "kilogramos", "toneladas", "cajas", "caja", "paquetes", "metros", "m", "pares",
    "equipos", "luminarias", "libros", "sillas", "notebooks", "computadoras", "bidones",
)

NUMBER_WORDS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "veinte": 20, "cien": 100, "mil": 1000,
}


def normalize(text: str | None) -> str:
    return _sin_acentos((text or "").lower())


def detection_reason(concepto: str | None, tipo_operacion: str | None) -> str | None:
    """Why an act is observable, or ``None`` when it is not."""
    text = normalize(concepto)
    if not text:
        return None
    if any(re.search(rf"\b{re.escape(k)}", text) for k in EXCLUDE_KEYWORDS):
        return None
    is_purchase = (tipo_operacion or "").lower() in PURCHASE_TYPES or any(v in text for v in PURCHASE_VERBS)
    if not is_purchase:
        return None
    # Match goods only in the object of the purchase, not in its destination
    # ("filtros para vehiculos" buys filters, not vehicles).
    obj = item_from_concepto(concepto) if any(v in text for v in PURCHASE_VERBS) else text
    for k in GOODS_KEYWORDS:
        if re.search(rf"\b{re.escape(k)}(?:s|es)?\b", obj):
            return f"compra de bien estandarizable: «{k}»"
    return None


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


@dataclass
class Observable:
    id: int
    fecha: str | None
    organismo: str | None
    concepto: str | None
    monto: float | None
    tipo_operacion: str | None
    etapa_gasto: str | None
    boletin_id: int | None
    boletin_url: str | None
    motivo: str


async def list_observables(
    db: AsyncSession,
    q: str | None = None,
    organismo: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Observable], int]:
    stmt = (
        select(EjecucionPresupuestaria, Boletin.source_url)
        .outerjoin(Boletin, Boletin.id == EjecucionPresupuestaria.boletin_id)
        .where(
            func.coalesce(EjecucionPresupuestaria.is_duplicate, 0) == 0,
            EjecucionPresupuestaria.monto > 0,
        )
        .order_by(EjecucionPresupuestaria.fecha_boletin.desc(), EjecucionPresupuestaria.id.desc())
    )
    if organismo:
        stmt = stmt.where(EjecucionPresupuestaria.organismo.ilike(f"%{organismo}%"))
    if fecha_desde:
        stmt = stmt.where(EjecucionPresupuestaria.fecha_boletin >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(EjecucionPresupuestaria.fecha_boletin <= fecha_hasta)

    rows = (await db.execute(stmt)).all()
    qn = normalize(q) if q else None
    found: list[Observable] = []
    for row, url in rows:
        reason = detection_reason(row.concepto, row.tipo_operacion)
        if not reason:
            continue
        if qn and qn not in normalize(f"{row.concepto} {row.organismo}"):
            continue
        found.append(_to_observable(row, url, reason))
    return found[offset: offset + limit], len(found)


def _to_observable(row: EjecucionPresupuestaria, url: str | None, reason: str) -> Observable:
    return Observable(
        id=row.id,
        fecha=row.fecha_boletin.isoformat() if row.fecha_boletin else None,
        organismo=row.organismo,
        concepto=row.concepto,
        monto=row.monto,
        tipo_operacion=row.tipo_operacion,
        etapa_gasto=row.etapa_gasto,
        boletin_id=row.boletin_id,
        boletin_url=url,
        motivo=reason,
    )


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


@dataclass
class Extraction:
    item: str
    cantidad: float | None
    unidad: str | None
    monto_total: float | None
    metodo: str  # "llm" | "regex"
    detalle: str | None = None
    fuente_cantidad: str | None = None  # "texto" | "compras_cba_grilla" | "compras_cba_pliego"
    renglones: list[dict] = field(default_factory=list)
    proceso: dict | None = None


_QTY_RE = re.compile(
    r"(?:(?P<word>" + "|".join(NUMBER_WORDS) + r")\s*\(\s*(?P<paren>\d[\d.]*)\s*\)|(?P<num>\d{1,3}(?:\.\d{3})+|\d+))\s+"
    r"(?P<unit>" + "|".join(sorted(UNIT_WORDS, key=len, reverse=True)) + r")\b"
)


def regex_extract(text: str) -> tuple[float | None, str | None]:
    """Quantity + unit from text like ``"5.000 resmas"`` or ``"dos (2) tráilers"``."""
    m = _QTY_RE.search(normalize(text))
    if not m:
        return None, None
    raw = m.group("paren") or m.group("num")
    try:
        qty = float(raw.replace(".", ""))
    except (TypeError, ValueError):
        return None, None
    return (qty if qty > 0 else None), m.group("unit")


def item_from_concepto(concepto: str | None) -> str:
    text = normalize(concepto)
    m = re.search(r"(?:adquisicion|compra|provision|suministro)\s+de\s+(.+)", text)
    item = m.group(1) if m else text
    item = re.split(r"\b(?:con destino|destinad[oa]s?|para|en el marco)\b", item)[0]
    return item.strip(" .,-")[:120]


EXTRACTION_PROMPT = """Extraé del siguiente acto de compra pública el bien comprado.
Respondé SOLO un JSON con las claves: item (texto corto, sin destino), cantidad (número o null),
unidad (texto o null), monto_total (número o null). No inventes la cantidad: si el texto no la dice, null.

Acto:
{texto}
"""


async def llm_extract(text: str, provider=None, timeout_s: float = 90.0) -> dict | None:
    """Ask the configured LLM (Ollama by default) for a JSON extraction."""
    try:
        if provider is None:
            from app.services.llm_provider import resolve_llm_provider

            provider = resolve_llm_provider()
        raw = await asyncio.wait_for(
            provider.generate_text(EXTRACTION_PROMPT.format(texto=text[:3000]), temperature=0.0, max_tokens=300),
            timeout=timeout_s,
        )
    except Exception as exc:
        logger.warning("precio-mercado: LLM extraction failed: %s", exc)
        return None
    m = re.search(r"\{.*\}", raw or "", flags=re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _num(value) -> float | None:
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d,]", "", value).replace(",", ".")
        try:
            v = float(cleaned)
            return v if v > 0 else None
        except ValueError:
            return None
    return None


def _text_supports(qty: float, text: str) -> bool:
    """True when the quantity literally appears in the text (``5000`` or ``5.000``)."""
    n = int(qty)
    if n != qty:
        return False
    forms = {str(n), f"{n:,}".replace(",", ".")}
    return any(re.search(rf"(?<![\d.]){re.escape(f)}(?![\d])", text) for f in forms)


async def extract(row: EjecucionPresupuestaria, fragment: str | None, provider=None, use_llm: bool = True) -> Extraction:
    text = " ".join(t for t in (row.concepto, fragment) if t)
    regex_qty, regex_unit = regex_extract(text)
    base_item = item_from_concepto(row.concepto)

    data = await llm_extract(text, provider=provider) if use_llm else None
    if data:
        llm_qty = _num(data.get("cantidad"))
        # The LLM may hallucinate a quantity; only accept one the text supports.
        if llm_qty and not _text_supports(llm_qty, text):
            llm_qty = None
        return Extraction(
            item=str(data.get("item") or base_item)[:120],
            cantidad=llm_qty or regex_qty,
            unidad=(data.get("unidad") or regex_unit) if (llm_qty or regex_qty) else None,
            monto_total=row.monto or _num(data.get("monto_total")),
            metodo="llm",
        )
    return Extraction(item=base_item, cantidad=regex_qty, unidad=regex_unit, monto_total=row.monto, metodo="regex")


# ---------------------------------------------------------------------------
# ComprasCba enrichment (quantities per renglón) with a persistent cache
# ---------------------------------------------------------------------------

CACHE_TTL_FOUND_S = 30 * 86400
CACHE_TTL_NOT_FOUND_S = 3 * 86400
CACHE_TTL_REFERENCES_S = 7 * 86400


def compras_cba_enabled() -> bool:
    return os.getenv("PRECIO_MERCADO_COMPRAS_CBA", "1").strip().lower() not in ("0", "false", "no")


async def cache_get(db: AsyncSession, key: str, ttl_s: float):
    from datetime import datetime

    row = await db.get(FuenteExternaCache, key)
    if row is None or row.fetched_at is None:
        return None
    if (datetime.utcnow() - row.fetched_at).total_seconds() > ttl_s:
        return None
    try:
        return json.loads(row.payload)
    except ValueError:
        return None


async def cache_set(db: AsyncSession, key: str, payload) -> None:
    from datetime import datetime

    row = await db.get(FuenteExternaCache, key)
    data = json.dumps(payload, ensure_ascii=False)
    if row is None:
        db.add(FuenteExternaCache(key=key, payload=data, fetched_at=datetime.utcnow()))
    else:
        row.payload, row.fetched_at = data, datetime.utcnow()
    await db.commit()


async def find_proceso(db: AsyncSession, row: EjecucionPresupuestaria, source: ComprasCbaSource,
                       cantidad_hint: float | None) -> ProcesoMatch:
    key = f"compras_cba:proceso:{row.id}"
    cached = await cache_get(db, key, CACHE_TTL_FOUND_S)
    if cached is not None:
        match = ProcesoMatch.from_dict(cached)
        if match.found or await cache_get(db, key, CACHE_TTL_NOT_FOUND_S) is not None:
            return match
    match = await source.find(row.fecha_boletin, row.monto, row.concepto, cantidad_hint)
    if match.found or (match.reason or "").startswith("ningún proceso"):
        await cache_set(db, key, match.to_dict())  # portal outages are not cached
    return match


def apply_renglones(ext: Extraction, match: ProcesoMatch) -> Extraction:
    """Fill quantity/unit from the process renglones when the act text had none."""
    if not match.found or match.proceso is None:
        return ext
    p = match.proceso
    ext.proceso = {"nro": p.nro, "tipo": p.tipo, "servicio": p.servicio, "objeto": p.objeto,
                   "estado": p.estado, "presupuesto_total": p.presupuesto_total,
                   "fecha_limite": p.fecha_limite, "documento": match.documento,
                   "origen": match.renglones_origen, "url": match.portal_url, "motivo": match.reason}
    ext.renglones = [asdict(r) for r in p.renglones]
    with_qty = [r for r in p.renglones if r.cantidad]
    if ext.cantidad is None and len(with_qty) == 1:
        ext.cantidad = with_qty[0].cantidad
        ext.unidad = ext.unidad or "unidades"
        ext.fuente_cantidad = f"compras_cba_{match.renglones_origen}"
    return ext


def references_loader(db: AsyncSession, source: ComprasCbaSource, fecha: date | None):
    """Async callable for ComprasCbaReferenceSource, cached per act month."""

    async def load() -> list[Proceso]:
        key = f"compras_cba:referencias:{(fecha or date.today()).strftime('%Y-%m')}"
        cached = await cache_get(db, key, CACHE_TTL_REFERENCES_S)
        if cached is None:
            procesos = await source.reference_renglones(fecha)
            cached = [asdict(p) for p in procesos]
            if cached:
                await cache_set(db, key, cached)
        out = []
        for d in cached:
            d = dict(d)
            d["renglones"] = [Renglon(**r) for r in d.get("renglones", [])]
            out.append(Proceso(**d))
        return out

    return load


# ---------------------------------------------------------------------------
# References and comparison
# ---------------------------------------------------------------------------


def item_tokens(item: str) -> list[str]:
    tokens = re.findall(r"[^\W_]+", normalize(item))
    return [t for t in dict.fromkeys(tokens) if len(t) > 2 and not t.isdigit() and t not in _FTS5_STOPWORDS][:4]


async def internal_references(db: AsyncSession, row: EjecucionPresupuestaria, item: str) -> SourceResult:
    """Similar purchase acts in the corpus whose unit price can be computed."""
    tokens = item_tokens(item)
    if not tokens:
        return SourceResult("corpus", True, reason="ítem sin palabras clave")
    main = tokens[0].rstrip("s")
    stmt = (
        select(EjecucionPresupuestaria, Boletin.source_url, Analisis.fragmento)
        .outerjoin(Boletin, Boletin.id == EjecucionPresupuestaria.boletin_id)
        .outerjoin(Analisis, Analisis.id == EjecucionPresupuestaria.analisis_id)
        .where(
            EjecucionPresupuestaria.id != row.id,
            func.coalesce(EjecucionPresupuestaria.is_duplicate, 0) == 0,
            EjecucionPresupuestaria.monto > 0,
            or_(EjecucionPresupuestaria.concepto.ilike(f"%{main}%"), and_(Analisis.fragmento.ilike(f"%{main}%"))),
        )
        .limit(200)
    )
    refs: list[PriceReference] = []
    similar = 0
    seen: set[tuple] = set()
    for other, url, fragment in (await db.execute(stmt)).all():
        if not detection_reason(other.concepto, other.tipo_operacion):
            continue
        # The same act is republished across days and sometimes attributed to
        # another organismo: the amount is the stable key, not the date.
        key = round(other.monto or 0)
        if key in seen or key == round(row.monto or 0):
            continue
        seen.add(key)
        similar += 1
        qty, unit = regex_extract(" ".join(t for t in (other.concepto, fragment) if t))
        if not qty:
            continue
        refs.append(PriceReference(
            source=f"Boletín oficial - {other.organismo or 's/organismo'}",
            description=(other.concepto or "")[:200],
            unit_price=other.monto / qty,
            observed_on=other.fecha_boletin.isoformat() if other.fecha_boletin else "",
            url=url,
            quantity=qty,
            unit=unit,
            kind="interna",
        ))
    reason = None if refs else f"{similar} actos similares en el corpus, ninguno con cantidad extraíble"
    return SourceResult("corpus", True, references=refs, reason=reason)


def classify(unit_price: float | None, references: list[PriceReference], th: Thresholds,
             motivo_sin_precio: str = "el acto no declara una cantidad extraíble") -> dict:
    prices = [r.unit_price for r in references if r.unit_price > 0]
    if unit_price is None:
        return {"clasificacion": "sin_datos_suficientes", "motivo": motivo_sin_precio,
                "mediana": statistics.median(prices) if prices else None, "desvio": None, "n_referencias": len(prices)}
    if len(prices) < th.min_references:
        return {"clasificacion": "sin_datos_suficientes",
                "motivo": f"{len(prices)} referencias (mínimo {th.min_references})",
                "mediana": statistics.median(prices) if prices else None, "desvio": None, "n_referencias": len(prices)}
    med = statistics.median(prices)
    desvio = (unit_price - med) / med
    if desvio > th.alerta:
        cls = "alerta"
    elif desvio > th.observable:
        cls = "observable"
    else:
        cls = "dentro_de_rango"
    return {"clasificacion": cls, "motivo": None, "mediana": med, "desvio": desvio, "n_referencias": len(prices)}


@dataclass
class AnalysisResult:
    acto: dict
    extraccion: dict
    precio_unitario: float | None
    comparacion: dict
    umbrales: dict
    fuentes: list[dict] = field(default_factory=list)
    referencias: list[dict] = field(default_factory=list)
    proveedor_llm: str | None = None
    aviso: str = ("Comparación orientativa con fuentes y fechas. No constituye dictamen: "
                  "precios de publicación y actos con distinto alcance pueden no ser comparables.")


async def analyze(
    db: AsyncSession,
    ejecucion_id: int,
    provider=None,
    external_sources: list[PriceSource] | None = None,
    thresholds: Thresholds | None = None,
    use_llm: bool = True,
    compras: ComprasCbaSource | None = None,
) -> AnalysisResult | None:
    th = thresholds or Thresholds.from_env()
    res = (await db.execute(
        select(EjecucionPresupuestaria, Boletin.source_url, Analisis.fragmento)
        .outerjoin(Boletin, Boletin.id == EjecucionPresupuestaria.boletin_id)
        .outerjoin(Analisis, Analisis.id == EjecucionPresupuestaria.analisis_id)
        .where(EjecucionPresupuestaria.id == ejecucion_id)
    )).first()
    if res is None:
        return None
    row, url, fragment = res

    if provider is None and use_llm:
        try:
            from app.services.llm_provider import resolve_llm_provider

            provider = resolve_llm_provider()
        except Exception as exc:
            logger.warning("precio-mercado: no LLM provider: %s", exc)
            use_llm = False

    ext = await extract(row, fragment, provider=provider, use_llm=use_llm)
    if ext.cantidad:
        ext.fuente_cantidad = "texto"
    if compras is None and compras_cba_enabled():
        compras = ComprasCbaSource()
    compras_status = None
    if compras is not None:
        match = await find_proceso(db, row, compras, ext.cantidad)
        ext = apply_renglones(ext, match)
        compras_status = SourceResult(
            "compras_cba", match.found or (match.reason or "").startswith("ningún proceso"),
            reason=(f"proceso {match.proceso.nro}: {len(match.proceso.renglones)} renglones ({match.renglones_origen or 'sin tabla'})"
                    + (f"; {match.reason}" if match.reason else "")) if match.found and match.proceso else match.reason,
        )
    unit_price = ext.monto_total / ext.cantidad if ext.monto_total and ext.cantidad else None
    motivo_sin_precio = "el acto no declara una cantidad extraíble"
    if unit_price is None and len([r for r in ext.renglones if r.get("cantidad")]) > 1:
        motivo_sin_precio = (f"{len(ext.renglones)} renglones de bienes distintos: el monto del acto no se "
                             "desglosa por renglón, no hay un precio unitario único")

    sources = external_sources if external_sources is not None else default_external_sources()
    if external_sources is None and compras is not None:
        sources = [*sources, ComprasCbaReferenceSource(references_loader(db, compras, row.fecha_boletin))]
    internal = await internal_references(db, row, ext.item)
    externals = await asyncio.gather(*(s.search(ext.item, ext.unidad) for s in sources), return_exceptions=True)
    results: list[SourceResult] = [internal]
    if compras_status is not None:
        results.append(compras_status)
    for s, r in zip(sources, externals, strict=True):
        results.append(r if isinstance(r, SourceResult) else SourceResult(getattr(s, "name", "?"), False, reason=f"no disponible ({r})"))

    # The act's own process is not a reference for itself.
    own = (ext.proceso or {}).get("nro")
    references = [ref for r in results for ref in r.references if not (own and ref.process_id == own)]
    comparison = classify(unit_price, references, th, motivo_sin_precio)

    reason = detection_reason(row.concepto, row.tipo_operacion)
    return AnalysisResult(
        acto=asdict(_to_observable(row, url, reason or "seleccionado por el usuario")),
        extraccion=asdict(ext),
        precio_unitario=unit_price,
        comparacion=comparison,
        umbrales=asdict(th),
        fuentes=[{"fuente": r.source, "disponible": r.available, "referencias": len(r.references), "motivo": r.reason} for r in results],
        referencias=[asdict(r) for r in references],
        proveedor_llm=(f"{getattr(provider, 'provider_id', '?')}:{getattr(provider, 'model_name', '?')}" if provider and use_llm else None),
    )
