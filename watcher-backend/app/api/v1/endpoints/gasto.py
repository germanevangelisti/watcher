"""Gasto público detectado en los boletines (M8, epic:precio-mercado).

- ``GET /gasto/detectado`` — listado con filtros, total y suma.

Lee `analisis` (no el ledger): M8 pide clasificar **todo acto con monto**, y
`ejecucion_presupuestaria` sólo contiene los actos que P.7 marcó como gasto
público.  Los dos universos son distintos a propósito y la respuesta declara
cuál es cuál:

- `tipo_gasto != no_es_gasto` es "esto parece gasto" (figura reconocida).
- `en_ledger` es "este acto está en el ledger de ejecución" (`is_gasto_publico`),
  que es la afirmación más fuerte y la que alimenta el contraste vs la Ley.

Un acto puede estar en el listado y no en el ledger: "Contrátase el servicio de
limpieza" es un servicio que el ciudadano tiene que ver, pero no trae evidencia
de etapa, así que P.7 lo deja fuera del ledger.  La fila muestra las dos cosas en
vez de mezclarlas.
"""

from datetime import date

from app.db.models import Analisis, Boletin, EjecucionPresupuestaria, PrecioMercadoAnalisis
from app.db.session import get_db
from app.services.presupuesto_matching import parse_date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Universo: actos con monto ya clasificados por M8.
_SIN_CLASIFICAR = "no_es_gasto"


def _filtros(
    tipo: list[str] | None,
    objeto: list[str] | None,
    nivel: list[str] | None,
    organismo: str | None,
    municipio: str | None,
    q: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    monto_min: float | None,
    monto_max: float | None,
    solo_gasto: bool,
) -> list:
    """Every WHERE clause, shared by the page query and the two aggregates.

    SQLite has no date type here: `boletines.date` is 'YYYYMMDD' as text, so the
    bounds are converted rather than compared as dates.  Comparing them as dates
    fails silently and returns everything.
    """
    where = [Analisis.monto_numerico > 0, Analisis.tipo_gasto.is_not(None)]
    if solo_gasto:
        where.append(Analisis.tipo_gasto != _SIN_CLASIFICAR)
    if tipo:
        where.append(Analisis.tipo_gasto.in_(tipo))
    if objeto:
        where.append(Analisis.objeto.in_(objeto))
    if nivel:
        where.append(Analisis.nivel.in_(nivel))
    if organismo:
        where.append(Analisis.organismo.ilike(f"%{organismo}%"))
    if municipio:
        where.append(Analisis.municipio.ilike(f"%{municipio}%"))
    if q:
        like = f"%{q}%"
        where.append(
            Analisis.descripcion.ilike(like)
            | Analisis.organismo.ilike(like)
            | Analisis.fragmento.ilike(like)
        )
    if fecha_desde:
        where.append(Boletin.date >= fecha_desde.strftime("%Y%m%d"))
    if fecha_hasta:
        where.append(Boletin.date <= fecha_hasta.strftime("%Y%m%d"))
    if monto_min is not None:
        where.append(Analisis.monto_numerico >= monto_min)
    if monto_max is not None:
        where.append(Analisis.monto_numerico <= monto_max)
    return where


@router.get("/detectado")
async def get_gasto_detectado(
    tipo: list[str] | None = Query(None, description="tipo_gasto: figura/procedimiento (repetible)"),
    objeto: list[str] | None = Query(None, description="obra | bien | servicio | transferencia | otro (repetible)"),
    nivel: list[str] | None = Query(None, description="provincial | municipal | comunal (repetible)"),
    organismo: str | None = None,
    municipio: str | None = None,
    q: str | None = Query(None, description="Texto en descripción u organismo"),
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    monto_min: float | None = Query(None, ge=0),
    monto_max: float | None = Query(None, ge=0),
    solo_gasto: bool = Query(True, description="Excluir los actos que no son gasto (no_es_gasto)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from_join = (
        select(Analisis, Boletin, EjecucionPresupuestaria.id.label("ejecucion_id"))
        .join(Boletin, Boletin.id == Analisis.boletin_id)
        .outerjoin(EjecucionPresupuestaria, EjecucionPresupuestaria.analisis_id == Analisis.id)
    )
    where = _filtros(
        tipo, objeto, nivel, organismo, municipio, q,
        fecha_desde, fecha_hasta, monto_min, monto_max, solo_gasto,
    )

    rows = (
        await db.execute(
            from_join.where(*where)
            .order_by(Boletin.date.desc(), Analisis.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    # Suma sobre el filtro entero, no sobre la página; y sin republicaciones.
    # Sumar `analisis` sin dedup cuenta dos veces el mismo acto (V.6: la
    # Licitación Pública 5576 de EPEC aparecía dos veces, $237,29B de más).
    canonico = func.coalesce(Analisis.is_duplicate_gasto, 0) == 0
    total, suma, suma_excluida = (
        await db.execute(
            select(
                func.count(),
                func.coalesce(func.sum(case((canonico, Analisis.monto_numerico), else_=0.0)), 0.0),
                func.coalesce(func.sum(case((~canonico, Analisis.monto_numerico), else_=0.0)), 0.0),
            )
            .select_from(Analisis)
            .join(Boletin, Boletin.id == Analisis.boletin_id)
            .where(*where)
        )
    ).one()

    # Última clasificación de precio por acto, para la página pedida.
    ejecucion_ids = [r.ejecucion_id for r in rows if r.ejecucion_id is not None]
    analyzed: dict[int, str] = {}
    if ejecucion_ids:
        clasificaciones = (
            await db.execute(
                select(PrecioMercadoAnalisis.ejecucion_id, PrecioMercadoAnalisis.clasificacion)
                .where(PrecioMercadoAnalisis.ejecucion_id.in_(ejecucion_ids))
                .order_by(PrecioMercadoAnalisis.id)
            )
        ).all()
        analyzed = {ej: cls for ej, cls in clasificaciones}

    items = []
    for analisis, boletin, ejecucion_id in rows:
        fecha = parse_date(boletin.date or "")
        # Qué es el acto, no por qué se clasificó así: el listado tiene que poder
        # mostrar la descripción, que es lo que el ciudadano lee para elegir.
        concepto = analisis.descripcion or (analisis.fragmento or "")[:200] or None
        items.append({
            "analisis_id": analisis.id,
            "ejecucion_id": ejecucion_id,
            "fecha": fecha.isoformat() if fecha else None,
            "boletin_id": boletin.id,
            "boletin_url": boletin.source_url,
            "organismo": analisis.organismo,
            "municipio": analisis.municipio,
            "nivel": analisis.nivel,
            "tipo_gasto": analisis.tipo_gasto,
            "objeto": analisis.objeto,
            "etapa_gasto": analisis.etapa_gasto,
            "concepto": concepto,
            "gasto_motivo": analisis.gasto_motivo,
            "monto": analisis.monto_numerico,
            "es_gasto_publico": analisis.tipo_gasto != _SIN_CLASIFICAR,
            "en_ledger": bool(analisis.is_gasto_publico),
            "is_duplicate_gasto": bool(analisis.is_duplicate_gasto),
            "ultima_clasificacion": analyzed.get(ejecucion_id) if ejecucion_id else None,
        })

    return {
        "total": total,
        "suma": suma,
        "republicaciones_excluidas": suma_excluida,
        "items": items,
    }
