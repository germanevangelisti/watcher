"""
Endpoints para procesamiento por lotes
"""

from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.batch import BatchProcessRequest
from app.services.batch_processor import BatchProcessor
from app.core.config import settings

router = APIRouter()

@router.post("/process/")
async def process_directory(
    request: BatchProcessRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Procesa un directorio de boletines en lotes.
    
    Args:
        request: Datos de la solicitud
        db: Sesión de base de datos
    """
    processor = BatchProcessor(db)
    source_dir = Path(request.source_dir)
    
    if not source_dir.exists():
        return {"error": "Directorio no encontrado"}
    
    stats = await processor.process_directory(
        source_dir=source_dir,
        batch_size=request.batch_size
    )
    return stats

@router.get("/stats/")
async def get_batch_stats(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Obtiene estadísticas del procesamiento por lotes.
    """
    # TODO: Implementar obtención de estadísticas desde la base de datos
    return {
        "total_processed": 0,
        "success_rate": 0,
        "last_batch": None
    }
