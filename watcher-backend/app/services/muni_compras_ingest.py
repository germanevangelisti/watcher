"""Ingest the Cordoba city procurement portal (MuniCompras) into the corpus.

One ``boletines`` row per **publication day** (``fuente='municipal_compras'``,
``section='portal_compras'``) and one ``analisis`` row per procedure, classified
with ``nivel='municipal'`` and ``municipio='Córdoba'`` set explicitly — the
source itself is the jurisdiction, so there is nothing to infer.

Two things this module is careful about:

- **The money is the official budget, not the award.**  The portal publishes
  ``presupuesto`` when the procedure is called; the awarded supplier and the
  awarded amount need a token and are not public.  So every row is
  ``etapa_gasto='llamado'`` and ``datos_extra['adjudicacion_publica']`` is
  ``False`` — a caller must not read ``monto_numerico`` as "what the city paid".
- **The same tender can be in the bulletin too.**  When the city calls a tender
  it publishes the resolution in the municipal bulletin *and* the procedure in
  the portal.  The bulletin act is the legal instrument, so the portal row is
  the one flagged ``is_duplicate_gasto`` and the spending total counts it once.

Idempotent by the portal's ``compra id``: a re-run updates rows in place, and a
procedure whose publication date changed moves to the right day instead of
being duplicated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from app.db.models import Analisis, Boletin
from app.scrapers.muni_compras import (
    COMPRAS_FUENTE,
    COMPRAS_MUNICIPIO,
    COMPRAS_NOT_FUENTE,
    CompraPublica,
    MuniComprasClient,
    clave_expediente,
    clave_titulo_portal,
    claves_expediente,
    claves_proceso,
    portal_url,
)
from app.services.gasto_classifier import (
    ETAPA_LLAMADO,
    JURISDICCION_MUNICIPAL,
    NIVEL_MUNICIPAL,
    OBJETO_NO_APLICA,
    OBJETO_OTRO,
    TIPO_COMPRA_DIRECTA,
    TIPO_CONCURSO_PRECIOS,
    TIPO_CONTRATACION,
    TIPO_LICITACION,
    TIPO_NO_ES_GASTO,
    TIPO_OTRO,
    TIPO_SUBASTA_ELECTRONICA,
    classify_objeto,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SECTION_PORTAL_COMPRAS = "portal_compras"
FRAGMENTO_MAX = 6000

ADJUDICACION_NOTA = (
    "el adjudicatario y el monto adjudicado no se publican en la API pública "
    "del portal (requieren token); el monto es el presupuesto oficial del llamado"
)

# Process type, from the portal's own vocabulary.  "SUBASTA DIRECTA" is a direct
# award dressed as an auction, so it counts as a compra directa; the electronic
# reverse auction is its own figure in Ley 10.155.
_TIPOS_PROCESO = (
    (("SUBASTA", "DIRECTA"), TIPO_COMPRA_DIRECTA),
    (("SUBASTA",), TIPO_SUBASTA_ELECTRONICA),
    (("CONCURSO",), TIPO_CONCURSO_PRECIOS),
    (("LICITACION",), TIPO_LICITACION),
    (("CONTRATACION",), TIPO_CONTRATACION),
)


def _fold(text: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", text or "") if not unicodedata.combining(c))


def tipo_gasto_de_compra(compra: CompraPublica) -> tuple[str, str]:
    """``(tipo_gasto, motivo)`` from the portal's process type."""
    hay = _fold(f"{compra.tipo_codigo or ''} {compra.tipo_nombre or ''}").upper()
    for needles, tipo in _TIPOS_PROCESO:
        if all(n in hay for n in needles):
            return tipo, f"portal de compras: {compra.tipo_nombre or compra.tipo_codigo}"
    return TIPO_OTRO, f"portal de compras: tipo de proceso no reconocido ({compra.tipo_nombre or compra.tipo_codigo})"


def texto_compra(compra: CompraPublica) -> str:
    """The row's searchable text: what it buys, who buys it and under which file."""
    partes = [compra.objeto]
    partes.append(f"{compra.tipo_nombre or compra.tipo_codigo or 'Procedimiento'} {compra.titulo}.")
    if compra.expediente:
        partes.append(f"Expediente {compra.expediente}.")
    organismo = " - ".join(p for p in (compra.entidad, compra.subentidad) if p)
    if organismo:
        partes.append(f"Organismo: {organismo}.")
    if compra.requirente:
        partes.append(f"Requirente: {compra.requirente}.")
    if compra.estado_nombre:
        partes.append(f"Estado: {compra.estado_nombre}.")
    return " ".join(p for p in partes if p)


def build_analisis_fields(compra: CompraPublica) -> dict:
    """Column values for one procedure's ``analisis`` row (pure, no I/O)."""
    tipo_gasto, motivo = tipo_gasto_de_compra(compra)
    texto = texto_compra(compra)
    objeto = classify_objeto(tipo_gasto, texto)
    if objeto == OBJETO_NO_APLICA:
        objeto = OBJETO_OTRO
    monto = compra.presupuesto
    return {
        "fragmento": texto[:FRAGMENTO_MAX],
        "tipo_acto": (compra.tipo_codigo or TIPO_OTRO).lower(),
        "numero_acto": (compra.titulo or f"compra {compra.id}")[:100],
        "organismo": compra.organismo[:200],
        "descripcion": compra.objeto or texto,
        "monto_numerico": monto,
        "monto_estimado": f"${monto:,.2f}" if monto else None,
        "montos_json": [monto] if monto else None,
        "riesgo": "informativo",
        # Spending, but only at the *call* stage: what is public is the official
        # budget, never the award.
        "is_gasto_publico": True,
        "etapa_gasto": ETAPA_LLAMADO,
        "jurisdiccion_gasto": JURISDICCION_MUNICIPAL,
        "tipo_gasto": tipo_gasto,
        "objeto": objeto,
        "nivel": NIVEL_MUNICIPAL,
        "municipio": COMPRAS_MUNICIPIO,
        "gasto_motivo": motivo,
        "is_duplicate_gasto": 0,
        "datos_extra": {
            "fuente": COMPRAS_FUENTE,
            "compra_id": compra.id,
            "titulo": compra.titulo,
            "tipo_compra": compra.tipo_codigo,
            "tipo_compra_nombre": compra.tipo_nombre,
            "estado": compra.estado_codigo,
            "estado_nombre": compra.estado_nombre,
            "expediente": compra.expediente,
            "entidad": compra.entidad,
            "subentidad": compra.subentidad,
            "requirente": compra.requirente,
            "fecha_publicacion": compra.fecha_publicacion.isoformat() if compra.fecha_publicacion else None,
            "fecha_creacion": compra.fecha_creacion.isoformat() if compra.fecha_creacion else None,
            "numero_llamados": compra.numero_llamados,
            "acta": compra.acta,
            "portal_url": portal_url(),
            "adjudicacion_publica": False,
            "adjudicacion_nota": ADJUDICACION_NOTA,
        },
    }


@dataclass
class ComprasIngestStats:
    compras: int = 0
    compras_nuevas: int = 0
    compras_con_monto: int = 0
    compras_gasto: int = 0
    duplicadas_boletin: int = 0
    monto_gasto: float = 0.0
    publicaciones: int = 0
    por_tipo: dict = field(default_factory=dict)
    por_estado: dict = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def boletin_filename(dia: date) -> str:
    """One synthetic edition per publication day; the name is the idempotency key."""
    return f"municipal_compras_{dia:%Y-%m-%d}.json"


async def _upsert_boletin(db: AsyncSession, dia: date, n_compras: int) -> Boletin:
    filename = boletin_filename(dia)
    boletin = (await db.execute(select(Boletin).where(Boletin.filename == filename))).scalar_one_or_none()
    if boletin is None:
        boletin = Boletin(filename=filename)
        db.add(boletin)
    boletin.date = dia.strftime("%Y%m%d")
    boletin.section = SECTION_PORTAL_COMPRAS
    boletin.status = "completed"
    boletin.fuente = COMPRAS_FUENTE
    boletin.origin = "synced"
    boletin.source_url = portal_url()
    boletin.seccion_nombre = f"Portal de Compras de Córdoba ({n_compras} compras publicadas)"
    await db.flush()
    return boletin


async def _portal_rows_by_compra_id(db: AsyncSession) -> dict[int, Analisis]:
    rows = (
        await db.execute(
            select(Analisis).join(Boletin, Boletin.id == Analisis.boletin_id).where(Boletin.fuente == COMPRAS_FUENTE)
        )
    ).scalars().all()
    index: dict[int, Analisis] = {}
    for row in rows:
        compra_id = (row.datos_extra or {}).get("compra_id")
        if compra_id is not None:
            index[int(compra_id)] = row
    return index


async def ingest_compras(
    db: AsyncSession,
    client: MuniComprasClient | None,
    desde: date,
    hasta: date,
    limit_paginas: int | None = None,
    compras: list[CompraPublica] | None = None,
) -> ComprasIngestStats:
    """Pull the range and upsert it.  ``compras`` skips the client (tests, replays)."""
    stats = ComprasIngestStats()
    if compras is None:
        if client is None:
            raise ValueError("ingest_compras necesita un cliente o una lista de compras")
        compras = list(client.iter_compras(desde, hasta, max_paginas=limit_paginas))

    por_dia: dict[date, list[CompraPublica]] = {}
    for compra in compras:
        dia = compra.fecha or hasta
        por_dia.setdefault(dia, []).append(compra)

    existentes = await _portal_rows_by_compra_id(db)
    for dia in sorted(por_dia):
        lote = por_dia[dia]
        boletin = await _upsert_boletin(db, dia, len(lote))
        for compra in lote:
            try:
                fields = build_analisis_fields(compra)
            except Exception as exc:  # noqa: BLE001 - one bad row must not stop the run
                stats.errores.append(f"compra {compra.id}: {exc}")
                continue
            row = existentes.get(compra.id)
            if row is None:
                row = Analisis(boletin_id=boletin.id)
                db.add(row)
                existentes[compra.id] = row
                stats.compras_nuevas += 1
            row.boletin_id = boletin.id
            for k, v in fields.items():
                setattr(row, k, v)
            stats.compras += 1
            stats.compras_con_monto += bool(fields["monto_numerico"])
            stats.por_tipo[fields["tipo_gasto"]] = stats.por_tipo.get(fields["tipo_gasto"], 0) + 1
            estado = compra.estado_codigo or compra.estado_nombre or "desconocido"
            stats.por_estado[estado] = stats.por_estado.get(estado, 0) + 1
        stats.publicaciones += 1
        await db.commit()
        logger.info("publicaciones %s: %d compras", dia, len(lote))

    await _limpiar_boletines_vacios(db)
    await marcar_duplicados_contra_boletin(db, stats)
    return stats


async def _limpiar_boletines_vacios(db: AsyncSession) -> int:
    """Drop portal days left with no procedure (a date that changed on re-run).

    Without this, moving a procedure to its real publication day would leave an
    empty "edición" behind and the coverage banner would count a day that
    publishes nothing.
    """
    from sqlalchemy import delete, exists

    huerfanos = (
        await db.execute(
            select(Boletin.id).where(
                Boletin.fuente == COMPRAS_FUENTE,
                ~exists().where(Analisis.boletin_id == Boletin.id),
            )
        )
    ).scalars().all()
    if huerfanos:
        await db.execute(delete(Boletin).where(Boletin.id.in_(huerfanos)))
        await db.commit()
        logger.info("boletines del portal sin compras eliminados: %d", len(huerfanos))
    return len(huerfanos)


async def marcar_duplicados_contra_boletin(db: AsyncSession, stats: ComprasIngestStats | None = None) -> None:
    """Flag portal rows whose tender is already in the municipal bulletin.

    Two identifiers, both published by the city: the file number
    (``Expediente N° 025522/26`` vs ``102-025180/2026``) and the tender number
    (``Licitación Pública N° 01/26`` vs the portal's ``2026/000001``).  The
    tender number alone is not enough — the same number can be reused across
    years and figures — so that match also requires the same amount.

    The bulletin act stays the counted row: it is the legal instrument, and it
    is already in the corpus.  Recompute totals for the whole portal source, so
    a re-run never leaves a stale flag behind.
    """
    boletin_rows = (
        await db.execute(
            select(Analisis)
            .join(Boletin, Boletin.id == Analisis.boletin_id)
            .where(
                Boletin.fuente == COMPRAS_NOT_FUENTE,
                Analisis.monto_numerico > 0,
                Analisis.tipo_gasto.is_not(None),
                Analisis.tipo_gasto != TIPO_NO_ES_GASTO,
            )
        )
    ).scalars().all()

    por_expediente: dict[str, Analisis] = {}
    por_proceso: dict[tuple[str, str], list[Analisis]] = {}
    for row in boletin_rows:
        texto = f"{row.descripcion or ''} {row.fragmento or ''}"
        for clave in claves_expediente(texto):
            por_expediente.setdefault(clave, row)
        for clave in claves_proceso(texto):
            por_proceso.setdefault(clave, []).append(row)

    portal_rows = (
        await db.execute(
            select(Analisis).join(Boletin, Boletin.id == Analisis.boletin_id).where(Boletin.fuente == COMPRAS_FUENTE)
        )
    ).scalars().all()

    gasto, monto, duplicadas = 0, 0.0, 0
    for row in portal_rows:
        extra = dict(row.datos_extra or {})
        match: Analisis | None = None
        motivo = None

        clave = clave_expediente(extra.get("expediente"))
        if clave and clave in por_expediente:
            match = por_expediente[clave]
            motivo = f"mismo expediente ({clave}) que el acto del Boletín Municipal"
        else:
            proceso = clave_titulo_portal(extra.get("titulo"))
            for candidato in por_proceso.get(proceso, []) if proceso else []:
                if row.monto_numerico and candidato.monto_numerico and abs(
                    candidato.monto_numerico - row.monto_numerico
                ) <= max(1.0, 0.005 * row.monto_numerico):
                    match, motivo = candidato, f"mismo llamado ({proceso[0]}/{proceso[1]}) y monto que el acto del Boletín Municipal"
                    break

        row.is_duplicate_gasto = 1 if match else 0
        if match:
            duplicadas += 1
            extra["dedupe"] = {"contra": COMPRAS_NOT_FUENTE, "analisis_id": match.id, "motivo": motivo}
        else:
            extra.pop("dedupe", None)
        row.datos_extra = extra

        if not match and row.monto_numerico:
            gasto += 1
            monto += row.monto_numerico

    await db.commit()
    if stats is not None:
        stats.compras_gasto, stats.monto_gasto, stats.duplicadas_boletin = gasto, monto, duplicadas
