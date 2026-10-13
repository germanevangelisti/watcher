"""Precio de mercado endpoints (epic:precio-mercado).

- ``GET  /precio-mercado/observables``          observable purchases from existing acts
- ``POST /precio-mercado/analizar/{ejecucion_id}`` user-triggered per-item analysis
- ``GET  /precio-mercado/analisis/{ejecucion_id}`` last stored analysis
- ``GET  /precio-mercado/config``               active thresholds
"""

import json
from dataclasses import asdict
from datetime import date

from app.db.models import PrecioMercadoAnalisis
from app.db.session import get_db
from app.services import precio_mercado_service as svc
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/config")
async def get_config():
    return {"umbrales": asdict(svc.Thresholds.from_env())}


@router.get("/observables")
async def get_observables(
    q: str | None = Query(None, description="Texto en concepto u organismo"),
    organismo: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    items, total = await svc.list_observables(db, q, organismo, fecha_desde, fecha_hasta, limit, offset)
    ids = [i.id for i in items]
    analyzed: dict[int, str] = {}
    if ids:
        rows = (await db.execute(
            select(PrecioMercadoAnalisis.ejecucion_id, PrecioMercadoAnalisis.clasificacion)
            .where(PrecioMercadoAnalisis.ejecucion_id.in_(ids))
            .order_by(PrecioMercadoAnalisis.id)
        )).all()
        analyzed = {eid: cls for eid, cls in rows}
    return {
        "total": total,
        "items": [{**asdict(i), "ultima_clasificacion": analyzed.get(i.id)} for i in items],
    }


@router.post("/analizar/{ejecucion_id}")
async def analizar(ejecucion_id: int, db: AsyncSession = Depends(get_db)):
    result = await svc.analyze(db, ejecucion_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Acto no encontrado")
    payload = asdict(result)
    db.add(PrecioMercadoAnalisis(
        ejecucion_id=ejecucion_id,
        clasificacion=result.comparacion["clasificacion"],
        proveedor_llm=result.proveedor_llm,
        resultado_json=json.dumps(payload, ensure_ascii=False),
    ))
    await db.commit()
    return payload


@router.get("/analisis/{ejecucion_id}")
async def ultimo_analisis(ejecucion_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(PrecioMercadoAnalisis)
        .where(PrecioMercadoAnalisis.ejecucion_id == ejecucion_id)
        .order_by(PrecioMercadoAnalisis.id.desc())
        .limit(1)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Sin análisis para este acto")
    return {**json.loads(row.resultado_json), "analizado_en": row.created_at.isoformat() if row.created_at else None}
