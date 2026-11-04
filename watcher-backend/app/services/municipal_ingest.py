"""Ingest the Cordoba municipal bulletin into ``boletines`` + ``analisis``.

One ``boletines`` row per edition (``fuente='municipal_capital'``) and one
``analisis`` row per act, classified with the same rules-based gasto
classifier the provincial pipeline uses, with ``nivel='municipal'`` and
``municipio='Córdoba'`` set explicitly: the source itself is the jurisdiction,
so there is nothing to infer.

Idempotent: editions are keyed by filename and acts by the API's
``publicacion_id`` (kept in ``datos_extra``), so a re-run updates rows in
place instead of duplicating them.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.db.models import Analisis, Boletin
from app.scrapers.pds_muni import (
    CORDOBA_FUENTE,
    CORDOBA_MUNICIPIO,
    CORDOBA_ORGANISMO,
    CordobaMunicipalClient,
    MunicipalActo,
    MunicipalEdicion,
    extract_monto,
    extract_pdf_text,
)
from app.services.gasto_classifier import (
    NIVEL_MUNICIPAL,
    SECCION_MUNICIPAL,
    TIPO_NO_ES_GASTO,
    classify_gasto,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SECTION_MUNICIPAL_CAPITAL = "municipal"
FRAGMENTO_MAX = 6000

# Acts of the Cordoba city bulletin that carry a large amount but do not
# dispose of public spending.  Matched on the subject (``Asunto``) only: the
# body of a licitacion also mentions fees and guarantees.
#   - debt issuance (Letras del Tesoro): financing, not spending;
#   - tariffs, fees and unit values (transporte, UEM, inscripciones): prices
#     the city charges, not money it pays;
#   - Tribunal de Cuentas rulings: they review spending, they do not make it.
_RE_MUNI_NO_GASTO = (
    (re.compile(r"letras?\s+del\s+tesoro|emision\s+de\s+(?:letras|titulos|bonos)|endeudamiento"
                r"|colocacion\s+de\s+(?:letras|titulos)", re.IGNORECASE),
     "emisi\u00f3n de deuda (Letras del Tesoro): financiamiento, no gasto"),
    (re.compile(r"tarifa|costo\s+de\s+(?:la\s+)?inscripcion|unidad\s+economica\s+municipal|\bu\.?e\.?m\b",
                re.IGNORECASE),
     "fija una tarifa o valor que cobra el municipio, no dispone gasto"),
    (re.compile(r"\bfallos?\s+(?:absolutori|condenatori)", re.IGNORECASE),
     "fallo del Tribunal de Cuentas: controla el gasto, no lo dispone"),
)


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))


# Debt acts often only say "se modifica la Resolucion X" in the subject; the
# VISTO header at the top of the body names the Letras del Tesoro.
CABECERA_DEUDA_MAX = 800


def motivo_no_gasto_municipal(asunto: str, texto: str = "") -> str | None:
    """Why a municipal act with a monto is not spending, or ``None``."""
    folded = _fold(asunto)
    for pattern, motivo in _RE_MUNI_NO_GASTO:
        if pattern.search(folded):
            return motivo
    deuda_re, deuda_motivo = _RE_MUNI_NO_GASTO[0]
    if texto and deuda_re.search(_fold(texto[:CABECERA_DEUDA_MAX])):
        return deuda_motivo
    return None


def clave_republicacion(asunto: str, monto: float | None) -> tuple[str, float] | None:
    """Same subject (folded, first 80 chars) and same monto = same act republished."""
    if not monto:
        return None
    norm = re.sub(r"[^a-z0-9]+", " ", _fold(asunto).lower()).strip()
    return norm[:80], round(monto, 2)


def edicion_filename(edicion: MunicipalEdicion) -> str:
    return f"municipal_cordoba_{edicion.numero}.pdf"


def build_analisis_fields(acto: MunicipalActo, texto: str) -> dict:
    """Column values for one act's ``analisis`` row (pure, no I/O)."""
    monto = extract_monto(texto) if texto else None
    organismo = CORDOBA_ORGANISMO + (f" - {acto.reparticion}" if acto.reparticion else "")
    cls = classify_gasto(
        {
            "tipo_acto": acto.tipo_acto,
            "descripcion": acto.asunto,
            "fragmento": texto[:FRAGMENTO_MAX],
            "organismo": CORDOBA_ORGANISMO,
        },
        section=SECCION_MUNICIPAL,
    )
    is_gasto, etapa, tipo_gasto, objeto = cls.is_gasto_publico, cls.etapa_gasto, cls.tipo_gasto, cls.objeto
    motivo = cls.tipo_gasto_motivo or cls.motivo
    excluido = motivo_no_gasto_municipal(acto.asunto, texto)
    if excluido:
        is_gasto, etapa, tipo_gasto, objeto, motivo = False, "no_aplica", TIPO_NO_ES_GASTO, "no_aplica", excluido
    return {
        "fragmento": (texto or acto.asunto)[:FRAGMENTO_MAX],
        "tipo_acto": acto.tipo_acto,
        "numero_acto": acto.numero_acto[:100],
        "organismo": organismo[:200],
        "descripcion": acto.asunto,
        "monto_numerico": monto,
        "monto_estimado": f"${monto:,.2f}" if monto else None,
        "montos_json": [monto] if monto else None,
        "riesgo": "informativo",
        "is_gasto_publico": is_gasto,
        "etapa_gasto": etapa,
        "jurisdiccion_gasto": cls.jurisdiccion,
        "tipo_gasto": tipo_gasto,
        "objeto": objeto,
        "nivel": NIVEL_MUNICIPAL,
        "municipio": CORDOBA_MUNICIPIO,
        "gasto_motivo": motivo,
        "is_duplicate_gasto": 0,
        "datos_extra": {
            "fuente": CORDOBA_FUENTE,
            "publicacion_id": acto.publicacion_id,
            "pdf_url": acto.pdf_url,
            "tipo_publicacion": acto.tipo_publicacion,
            "reparticion": acto.reparticion,
            "fecha_sancion": acto.fecha_sancion.isoformat() if acto.fecha_sancion else None,
            "texto_extraido": bool(texto),
        },
    }


@dataclass
class IngestStats:
    ediciones: int = 0
    actos: int = 0
    actos_nuevos: int = 0
    actos_con_texto: int = 0
    actos_con_monto: int = 0
    actos_gasto: int = 0
    republicaciones: int = 0
    monto_gasto: float = 0.0
    errores: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


async def _upsert_boletin(db: AsyncSession, edicion: MunicipalEdicion, n_actos: int) -> Boletin:
    filename = edicion_filename(edicion)
    boletin = (await db.execute(select(Boletin).where(Boletin.filename == filename))).scalar_one_or_none()
    if boletin is None:
        boletin = Boletin(filename=filename)
        db.add(boletin)
    boletin.date = edicion.fecha.strftime("%Y%m%d")
    boletin.section = SECTION_MUNICIPAL_CAPITAL
    boletin.status = "completed"
    boletin.fuente = CORDOBA_FUENTE
    boletin.origin = "synced"
    boletin.source_url = edicion.pdf_url
    boletin.seccion_nombre = f"Boletín Municipal de Córdoba N° {edicion.numero} ({n_actos} actos)"
    await db.flush()
    return boletin


async def ingest_edicion(
    db: AsyncSession,
    edicion: MunicipalEdicion,
    actos: list[MunicipalActo],
    get_text: Callable[[MunicipalActo], str],
    stats: IngestStats,
) -> None:
    boletin = await _upsert_boletin(db, edicion, len(actos))
    existing = {
        (a.datos_extra or {}).get("publicacion_id"): a
        for a in (await db.execute(select(Analisis).where(Analisis.boletin_id == boletin.id))).scalars()
    }
    for acto in actos:
        try:
            texto = get_text(acto) or ""
        except Exception as exc:  # noqa: BLE001 - one bad PDF must not stop the run
            stats.errores.append(f"pub {acto.publicacion_id}: {exc}")
            texto = ""
        fields = build_analisis_fields(acto, texto)
        row = existing.get(acto.publicacion_id)
        if row is None:
            row = Analisis(boletin_id=boletin.id)
            db.add(row)
            stats.actos_nuevos += 1
        for k, v in fields.items():
            setattr(row, k, v)
        stats.actos += 1
        stats.actos_con_texto += bool(texto)
        stats.actos_con_monto += bool(fields["monto_numerico"])
    stats.ediciones += 1
    await db.commit()


def pdf_text_getter(client: CordobaMunicipalClient, max_pages: int = 6) -> Callable[[MunicipalActo], str]:
    def _get(acto: MunicipalActo) -> str:
        if not acto.pdf_url:
            return ""
        path: Path = client.download(acto.pdf_url, client.acto_pdf_path(acto))
        return extract_pdf_text(path, max_pages=max_pages)

    return _get


async def ingest_cordoba(
    db: AsyncSession,
    client: CordobaMunicipalClient,
    desde: date,
    hasta: date,
    limit_ediciones: int | None = None,
    get_text: Callable[[MunicipalActo], str] | None = None,
) -> IngestStats:
    stats = IngestStats()
    get_text = get_text or pdf_text_getter(client)
    for edicion, actos in client.iter_ediciones(desde, hasta):
        if limit_ediciones is not None and stats.ediciones >= limit_ediciones:
            break
        await ingest_edicion(db, edicion, actos, get_text, stats)
        logger.info("edicion %s (%s): %d actos", edicion.numero, edicion.fecha, len(actos))
    await marcar_republicaciones(db, stats)
    return stats


async def marcar_republicaciones(db: AsyncSession, stats: IngestStats | None = None) -> None:
    """Flag republished municipal acts and recompute the gasto totals.

    The city republishes a tender call on consecutive days (Licitacion 01/26 of
    the Tribunal de Cuentas appears three times).  Like the provincial ledger,
    the first publication counts and the rest are listed but not summed.  Runs
    over the whole municipal corpus, in publication order.
    """
    rows = (
        await db.execute(
            select(Analisis)
            .join(Boletin, Boletin.id == Analisis.boletin_id)
            .where(Boletin.fuente == CORDOBA_FUENTE)
            .order_by(Boletin.date, Analisis.id)
        )
    ).scalars().all()
    vistos: set = set()
    actos_gasto, republicaciones, monto = 0, 0, 0.0
    for row in rows:
        es_gasto = bool(row.monto_numerico) and row.tipo_gasto not in (None, TIPO_NO_ES_GASTO)
        clave = clave_republicacion(row.descripcion or "", row.monto_numerico) if es_gasto else None
        duplicado = clave is not None and clave in vistos
        row.is_duplicate_gasto = 1 if duplicado else 0
        if clave is not None:
            vistos.add(clave)
        if es_gasto and not duplicado:
            actos_gasto += 1
            monto += row.monto_numerico
        republicaciones += duplicado
    await db.commit()
    if stats is not None:
        stats.actos_gasto, stats.republicaciones, stats.monto_gasto = actos_gasto, republicaciones, monto
