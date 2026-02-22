"""
Health check endpoint for monitoring and load-balancer probes.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Returns service health including database and vector store status.
    """
    checks: dict = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "database": "unknown",
        "chromadb": "unknown",
    }

    # Check relational DB
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"Health check DB failed: {e}")
        checks["database"] = "error"
        checks["status"] = "degraded"

    # Check ChromaDB
    try:
        from app.services.embedding_service import get_embedding_service
        svc = get_embedding_service()
        if svc.collection:
            count = svc.collection.count()
            checks["chromadb"] = "ok"
            checks["chromadb_documents"] = count
        else:
            checks["chromadb"] = "not_initialized"
    except Exception as e:
        logger.warning(f"Health check ChromaDB: {e}")
        checks["chromadb"] = "unavailable"

    return checks
