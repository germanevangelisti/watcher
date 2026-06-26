"""
CRUD de Fuentes de Datos por jurisdicción.

Gestiona URLs de acceso a fuentes de datos públicos:
  - boletin_diario       : URL template del boletín oficial
  - presupuesto_anual    : URL del presupuesto del ejercicio
  - ejecucion_trimestral : URL de informes de ejecución presupuestaria
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import FuenteDato, Jurisdiccion, Boletin
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

TIPOS_VALIDOS = {"boletin_diario", "presupuesto_anual", "ejecucion_trimestral"}


class FuenteDatoRequest(BaseModel):
    jurisdiccion_id: int
    tipo: str = Field(description="boletin_diario | presupuesto_anual | ejecucion_trimestral")
    nombre: str = Field(max_length=200)
    url_template: Optional[str] = None
    activa: bool = True
    descripcion: Optional[str] = None


class FuenteDatoUpdateRequest(BaseModel):
    nombre: Optional[str] = Field(None, max_length=200)
    url_template: Optional[str] = None
    activa: Optional[bool] = None
    descripcion: Optional[str] = None


def _serialize(f: FuenteDato, jurisdiccion_nombre: Optional[str] = None) -> Dict:
    return {
        "id": f.id,
        "jurisdiccion_id": f.jurisdiccion_id,
        "jurisdiccion_nombre": jurisdiccion_nombre,
        "tipo": f.tipo,
        "nombre": f.nombre,
        "url_template": f.url_template,
        "activa": f.activa,
        "descripcion": f.descripcion,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
    }


@router.get("")
@router.get("/")
async def list_fuentes_dato(
    jurisdiccion_id: Optional[int] = Query(None, description="Filtrar por jurisdicción"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """Lista fuentes de datos, opcionalmente filtradas por jurisdicción y/o tipo."""
    stmt = select(FuenteDato, Jurisdiccion.nombre).outerjoin(
        Jurisdiccion, FuenteDato.jurisdiccion_id == Jurisdiccion.id
    )
    if jurisdiccion_id is not None:
        stmt = stmt.where(FuenteDato.jurisdiccion_id == jurisdiccion_id)
    if tipo is not None:
        stmt = stmt.where(FuenteDato.tipo == tipo)
    stmt = stmt.order_by(FuenteDato.jurisdiccion_id, FuenteDato.tipo)

    result = await db.execute(stmt)
    return [_serialize(f, nombre) for f, nombre in result.all()]


@router.get("/{fuente_id}")
async def get_fuente_dato(fuente_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
    """Detalle de una fuente de datos."""
    stmt = select(FuenteDato, Jurisdiccion.nombre).outerjoin(
        Jurisdiccion, FuenteDato.jurisdiccion_id == Jurisdiccion.id
    ).where(FuenteDato.id == fuente_id)
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"FuenteDato {fuente_id} no encontrada")
    f, nombre = row
    return _serialize(f, nombre)


@router.post("", status_code=201)
@router.post("/", status_code=201, include_in_schema=False)
async def create_fuente_dato(body: FuenteDatoRequest, db: AsyncSession = Depends(get_db)) -> Dict:
    """Crea una nueva fuente de datos para una jurisdicción."""
    if body.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Valores: {TIPOS_VALIDOS}")

    # Verificar que la jurisdicción existe
    j = await db.get(Jurisdiccion, body.jurisdiccion_id)
    if not j:
        raise HTTPException(status_code=404, detail=f"Jurisdicción {body.jurisdiccion_id} no encontrada")

    # Verificar unicidad (jurisdiccion_id, tipo)
    existing = await db.execute(
        select(FuenteDato)
        .where(FuenteDato.jurisdiccion_id == body.jurisdiccion_id)
        .where(FuenteDato.tipo == body.tipo)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una fuente de tipo '{body.tipo}' para la jurisdicción {body.jurisdiccion_id}",
        )

    fuente = FuenteDato(
        jurisdiccion_id=body.jurisdiccion_id,
        tipo=body.tipo,
        nombre=body.nombre,
        url_template=body.url_template,
        activa=body.activa,
        descripcion=body.descripcion,
    )
    db.add(fuente)
    await db.commit()
    await db.refresh(fuente)
    return _serialize(fuente, j.nombre)


@router.put("/{fuente_id}")
async def update_fuente_dato(
    fuente_id: int, body: FuenteDatoUpdateRequest, db: AsyncSession = Depends(get_db)
) -> Dict:
    """Actualiza nombre, url_template, activa o descripcion de una fuente."""
    fuente = await db.get(FuenteDato, fuente_id)
    if not fuente:
        raise HTTPException(status_code=404, detail=f"FuenteDato {fuente_id} no encontrada")

    if body.nombre is not None:
        fuente.nombre = body.nombre
    if body.url_template is not None:
        fuente.url_template = body.url_template
    if body.activa is not None:
        fuente.activa = body.activa
    if body.descripcion is not None:
        fuente.descripcion = body.descripcion

    await db.commit()
    await db.refresh(fuente)

    j = await db.get(Jurisdiccion, fuente.jurisdiccion_id)
    return _serialize(fuente, j.nombre if j else None)


@router.delete("/{fuente_id}", status_code=204)
async def delete_fuente_dato(fuente_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina una fuente de datos."""
    fuente = await db.get(FuenteDato, fuente_id)
    if not fuente:
        raise HTTPException(status_code=404, detail=f"FuenteDato {fuente_id} no encontrada")
    await db.delete(fuente)
    await db.commit()


@router.post("/{fuente_id}/upload", status_code=201)
async def upload_fuente_dato(
    fuente_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Sube un PDF para una fuente de tipo presupuesto_anual o ejecucion_trimestral.
    Guarda el archivo en UPLOADS_DIR y crea un Boletin con origin='uploaded', status='pending'.
    """
    fuente = await db.get(FuenteDato, fuente_id)
    if not fuente:
        raise HTTPException(status_code=404, detail=f"FuenteDato {fuente_id} no encontrada")
    if fuente.tipo == "boletin_diario":
        raise HTTPException(status_code=400, detail="Upload no disponible para boletin_diario. Usa trigger-from-date.")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    # Save file
    dest_dir = settings.UPLOADS_DIR / str(fuente.jurisdiccion_id) / fuente.tipo
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file.filename
    contents = await file.read()
    dest_path.write_bytes(contents)

    # Create Boletin record
    boletin = Boletin(
        filename=file.filename,
        origin="uploaded",
        jurisdiccion_id=fuente.jurisdiccion_id,
        status="pending",
        source_url=None,
    )
    db.add(boletin)
    await db.commit()
    await db.refresh(boletin)

    logger.info(f"Uploaded {file.filename} for fuente {fuente_id} → boletin_id={boletin.id}")
    return {
        "boletin_id": boletin.id,
        "filename": file.filename,
        "message": "Archivo subido. Procesalo desde la página de Pipeline.",
    }
