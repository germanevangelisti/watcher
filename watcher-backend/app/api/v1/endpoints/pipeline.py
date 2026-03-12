"""
Pipeline endpoints - Unified document processing pipeline

Provides endpoints for:
- Resetting all processed data (total and per document)
- Processing single documents through the complete pipeline
- Batch processing all pending documents
- Checking pipeline status and statistics
- Getting default pipeline configuration
"""

import asyncio
import logging
import uuid
import calendar as _cal_module
from datetime import date as _date
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from app.db.session import get_db
from app.db.models import Boletin, ChunkRecord, Analisis, FuenteDato
from app.services.url_fetcher import build_url_from_template
from app.core.config import settings
from app.core.events import event_bus, EventType
from app.schemas.pipeline import (
    PipelineConfig,
    ExtractionConfig,
    EnrichmentConfig,
    IndexingConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory session tracking for active pipeline runs
_active_sessions: Dict[str, Dict[str, Any]] = {}

# SQLite allows only one writer at a time. This semaphore serialises all DB
# write phases across concurrently-running background pipeline tasks so that
# sections never race on the same SQLite file.  Under PostgreSQL this lock is
# never acquired (see usage sites below).
_sqlite_write_lock = asyncio.Semaphore(1)

# Section names — duplicated here to avoid circular import with boletines.py
_PIPELINE_SECTION_NAMES = {
    "1": "Legislación y Normativas",
    "2": "Judiciales",
    "3": "Sociedades y Personas Jurídicas",
    "4": "Notificaciones, Licitaciones y Contrataciones",
    "5": "Municipalidades y Comunas",
}

# ---------------------------------------------------------------------------
# Lazy singletons for expensive services (BUG-1: wire firewall + AIU once)
# ---------------------------------------------------------------------------
_watcher_singleton: Optional[Any] = None
_aiu_singleton: Optional[Any] = None
_svc_init_lock: Optional[Any] = None


def _get_svc_lock():
    global _svc_init_lock
    import asyncio
    if _svc_init_lock is None:
        _svc_init_lock = asyncio.Lock()
    return _svc_init_lock


async def _get_watcher_and_aiu():
    """Return (WatcherService, AIUService) singletons, initialised lazily."""
    global _watcher_singleton, _aiu_singleton
    if _watcher_singleton is None:
        async with _get_svc_lock():
            if _watcher_singleton is None:
                from app.services.watcher_service import WatcherService
                from app.services.aiu_service import AIUService
                ws = WatcherService()
                aiu_svc = AIUService(gemini_model=getattr(ws, "model", None))
                ws.set_aiu_service(aiu_svc)
                _aiu_singleton = aiu_svc
                _watcher_singleton = ws
    return _watcher_singleton, _aiu_singleton


# =============================================================================
# RESET ENDPOINTS
# =============================================================================

@router.post("/reset")
async def reset_all_pipeline_data(
    db: AsyncSession = Depends(get_db),
    x_confirm_reset: Optional[str] = Header(None, alias="X-Confirm-Reset"),
):
    """
    Reset ALL processed data. Requires confirmation header.
    
    This is a destructive operation that will:
    - Delete all chunk_records from SQLite
    - Clear ChromaDB collection
    - Delete all .txt files from data/processed/
    - Reset all boletines to status='pending'
    
    Requires header: X-Confirm-Reset: RESET_ALL_DATA
    """
    if x_confirm_reset != "RESET_ALL_DATA":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Esta operacion eliminara TODOS los datos procesados (chunks, embeddings, textos extraidos). "
                           "Esta accion NO se puede deshacer.",
                "confirm": "Enviar header 'X-Confirm-Reset: RESET_ALL_DATA' para confirmar.",
                "affected": [
                    "Todos los chunk_records en SQLite",
                    "Todos los embeddings en ChromaDB",
                    "Todos los archivos .txt en data/processed/",
                    "Status de todos los boletines -> pending",
                ]
            }
        )
    
    try:
        results = {
            "chunks_deleted": 0,
            "analisis_deleted": 0,
            "chromadb_cleared": False,
            "txt_files_deleted": 0,
            "boletines_reset": 0,
        }
        
        # 1. Delete all chunk_records
        count_result = await db.execute(select(func.count()).select_from(ChunkRecord))
        results["chunks_deleted"] = count_result.scalar() or 0
        await db.execute(delete(ChunkRecord))
        
        # 1b. Delete all analisis records
        count_result = await db.execute(select(func.count()).select_from(Analisis))
        results["analisis_deleted"] = count_result.scalar() or 0
        await db.execute(delete(Analisis))
        
        # 2. Clear ChromaDB collection
        try:
            from app.services.embedding_service import get_embedding_service
            service = get_embedding_service()
            if service.client and service.collection:
                # Delete and recreate collection
                collection_name = service.collection.name
                service.client.delete_collection(collection_name)
                service.collection = service.client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=service.embedding_fn,
                )
                results["chromadb_cleared"] = True
                logger.info("ChromaDB collection cleared and recreated")
        except Exception as e:
            logger.warning(f"ChromaDB reset skipped: {e}")
            results["chromadb_cleared"] = False
        
        # 3. Delete .txt files from data/processed/
        processed_dir = settings.DATA_DIR / "processed"
        if processed_dir.exists():
            txt_files = list(processed_dir.glob("*.txt"))
            results["txt_files_deleted"] = len(txt_files)
            for txt_file in txt_files:
                try:
                    txt_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete {txt_file}: {e}")
        
        # 4. Reset all boletines to pending
        count_result = await db.execute(
            select(func.count()).select_from(Boletin).where(Boletin.status != "pending")
        )
        results["boletines_reset"] = count_result.scalar() or 0
        await db.execute(
            update(Boletin).values(status="pending", error_message=None)
        )
        
        await db.commit()
        
        # Emit event
        await event_bus.emit(
            EventType.PIPELINE_RESET,
            data=results,
            source="pipeline"
        )
        
        logger.info(f"Pipeline reset complete: {results}")
        return {"success": True, "message": "Todos los datos procesados han sido eliminados.", **results}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in pipeline reset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{boletin_id}")
async def reset_document_pipeline(
    boletin_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset processed data for a single document.
    
    Deletes chunks, embeddings, and extracted text for this document,
    then resets its status to 'pending'.
    Useful for reprocessing with different pipeline configurations.
    """
    try:
        # Find the boletin
        result = await db.execute(select(Boletin).where(Boletin.id == boletin_id))
        boletin = result.scalar_one_or_none()
        
        if not boletin:
            raise HTTPException(status_code=404, detail=f"Boletin {boletin_id} no encontrado")
        
        results = {
            "boletin_id": boletin_id,
            "filename": boletin.filename,
            "chunks_deleted": 0,
            "analisis_deleted": 0,
            "chromadb_deleted": 0,
            "txt_deleted": False,
            "previous_status": boletin.status,
        }
        
        # Build the document_id used in chunk_records
        document_id = boletin.filename.replace(".pdf", "")
        
        # 0. Delete analisis records for this boletin
        count_result = await db.execute(
            select(func.count()).select_from(Analisis).where(
                Analisis.boletin_id == boletin_id
            )
        )
        results["analisis_deleted"] = count_result.scalar() or 0
        await db.execute(
            delete(Analisis).where(Analisis.boletin_id == boletin_id)
        )
        
        # 1. Delete chunk_records for this boletin
        count_result = await db.execute(
            select(func.count()).select_from(ChunkRecord).where(
                (ChunkRecord.boletin_id == boletin_id) | 
                (ChunkRecord.document_id == document_id)
            )
        )
        results["chunks_deleted"] = count_result.scalar() or 0
        
        await db.execute(
            delete(ChunkRecord).where(
                (ChunkRecord.boletin_id == boletin_id) | 
                (ChunkRecord.document_id == document_id)
            )
        )
        
        # 2. Delete from ChromaDB
        try:
            from app.services.embedding_service import get_embedding_service
            service = get_embedding_service()
            if service.collection:
                # Try to delete by document_id metadata filter
                try:
                    existing = service.collection.get(
                        where={"document_id": document_id}
                    )
                    if existing and existing["ids"]:
                        service.collection.delete(ids=existing["ids"])
                        results["chromadb_deleted"] = len(existing["ids"])
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"ChromaDB delete skipped for {document_id}: {e}")
        
        # 3. Delete .txt file
        txt_filename = boletin.filename.replace(".pdf", ".txt")
        txt_path = settings.DATA_DIR / "processed" / txt_filename
        if txt_path.exists():
            txt_path.unlink()
            results["txt_deleted"] = True
        
        # 4. Reset status to pending
        boletin.status = "pending"
        boletin.error_message = None
        
        await db.commit()
        
        # Emit event
        await event_bus.emit(
            EventType.PIPELINE_RESET_DOCUMENT,
            data=results,
            source="pipeline"
        )
        
        logger.info(f"Document {boletin_id} reset: {results}")
        return {"success": True, **results}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error resetting document {boletin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROCESSING ENDPOINTS
# =============================================================================

@router.post("/process/{boletin_id}")
async def process_single_document(
    boletin_id: int,
    config: Optional[PipelineConfig] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a single document through the pipeline with optional configuration.
    
    Runs as a background task. Status updates are emitted via WebSocket.
    """
    try:
        # Find the boletin
        result = await db.execute(select(Boletin).where(Boletin.id == boletin_id))
        boletin = result.scalar_one_or_none()
        
        if not boletin:
            raise HTTPException(status_code=404, detail=f"Boletin {boletin_id} no encontrado")
        
        session_id = str(uuid.uuid4())[:8]
        pipeline_config = config or PipelineConfig()
        
        # Update status to extracting
        boletin.status = "extracting"
        await db.commit()
        
        # Emit pipeline.started so the frontend tracks progress
        await event_bus.emit(
            EventType.PIPELINE_STARTED,
            data={
                "session_id": session_id,
                "total": 1,
                "config": pipeline_config.model_dump(),
            },
            source="pipeline"
        )
        
        # Run in background
        background_tasks.add_task(
            _process_document_pipeline,
            boletin_id,
            boletin.filename,
            session_id,
            pipeline_config,
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "boletin_id": boletin_id,
            "filename": boletin.filename,
            "message": "Procesamiento iniciado",
            "config": pipeline_config.model_dump(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting pipeline for {boletin_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-all")
async def process_all_pending(
    config: Optional[PipelineConfig] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    """
    Process all pending documents through the pipeline.
    
    Runs as a background task. Status updates are emitted via WebSocket.
    Returns immediately with session_id for tracking.
    """
    try:
        pipeline_config = config or PipelineConfig()
        
        # Get all pending boletines
        result = await db.execute(
            select(Boletin.id, Boletin.filename)
            .where(Boletin.status.in_(["pending", "failed"]))
            .order_by(Boletin.id)
        )
        pending = result.all()
        
        if not pending:
            return {
                "success": True,
                "session_id": None,
                "total": 0,
                "message": "No hay documentos pendientes de procesar",
            }
        
        session_id = str(uuid.uuid4())[:8]
        boletin_list = [{"id": row.id, "filename": row.filename} for row in pending]
        
        # Track session
        _active_sessions[session_id] = {
            "total": len(boletin_list),
            "current": 0,
            "status": "running",
            "config": pipeline_config.model_dump(),
            "errors": [],
        }
        
        # Emit pipeline started
        await event_bus.emit(
            EventType.PIPELINE_STARTED,
            data={
                "session_id": session_id,
                "total": len(boletin_list),
                "config": pipeline_config.model_dump(),
            },
            source="pipeline"
        )
        
        # Run in background
        background_tasks.add_task(
            _process_all_pipeline,
            boletin_list,
            session_id,
            pipeline_config,
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "total": len(boletin_list),
            "message": f"Procesamiento de {len(boletin_list)} documentos iniciado",
            "config": pipeline_config.model_dump(),
        }
    
    except Exception as e:
        logger.error(f"Error starting batch pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CALENDAR TRIGGER ENDPOINTS
# =============================================================================

class TriggerFromDateRequest(BaseModel):
    jurisdiccion_id: int
    date: str    # "YYYYMMDD"
    section: str # "1" … "5"


class TriggerMonthRequest(BaseModel):
    jurisdiccion_id: int
    year: int
    month: int
    sections: List[str] = ["1", "2", "3", "4", "5"]


@router.post("/trigger-from-date")
async def trigger_from_date(
    req: TriggerFromDateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Create (or reuse) a Boletin for a given date+section and trigger the pipeline.
    Fetches the PDF from the configured FuenteDato URL — no file on disk required.
    """
    # 1. Look up active FuenteDato for this jurisdiccion
    fuente_result = await db.execute(
        select(FuenteDato).where(
            FuenteDato.jurisdiccion_id == req.jurisdiccion_id,
            FuenteDato.tipo == "boletin_diario",
            FuenteDato.activa,
        )
    )
    fuente = fuente_result.scalar_one_or_none()
    if not fuente or not fuente.url_template:
        raise HTTPException(
            status_code=404,
            detail=f"No hay fuente de datos activa para jurisdiccion_id={req.jurisdiccion_id}",
        )

    # 2. Build filename + source URL
    filename = f"{req.date}_{req.section}_Secc.pdf"
    source_url = build_url_from_template(fuente.url_template, filename)

    # 3. Upsert Boletin
    boletin_result = await db.execute(select(Boletin).where(Boletin.filename == filename))
    boletin = boletin_result.scalar_one_or_none()

    if boletin is None:
        boletin = Boletin(
            filename=filename,
            date=req.date,
            section=req.section,
            seccion_nombre=_PIPELINE_SECTION_NAMES.get(req.section),
            status="pending",
            jurisdiccion_id=req.jurisdiccion_id,
            source_url=source_url,
        )
        db.add(boletin)
        await db.flush()  # populate boletin.id
    elif boletin.status == "completed":
        return {
            "success": True,
            "boletin_id": boletin.id,
            "filename": filename,
            "source_url": source_url,
            "message": "Ya procesado — ver resultados",
            "already_completed": True,
        }

    if not boletin.source_url:
        boletin.source_url = source_url
    boletin.status = "extracting"
    await db.commit()

    session_id = str(uuid.uuid4())[:8]
    await event_bus.emit(
        EventType.PIPELINE_STARTED,
        data={"session_id": session_id, "total": 1, "config": PipelineConfig().model_dump()},
        source="pipeline",
    )
    background_tasks.add_task(
        _process_document_pipeline,
        boletin.id,
        filename,
        session_id,
        PipelineConfig(),
    )

    return {
        "success": True,
        "boletin_id": boletin.id,
        "session_id": session_id,
        "filename": filename,
        "source_url": source_url,
        "message": "Procesamiento iniciado",
    }


@router.post("/trigger-month")
async def trigger_month(
    req: TriggerMonthRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk-trigger pipeline for all pending/not-found sections in a month.
    Creates Boletin records for missing weekday+section combos and queues them.
    """
    # 1. Look up active FuenteDato
    fuente_result = await db.execute(
        select(FuenteDato).where(
            FuenteDato.jurisdiccion_id == req.jurisdiccion_id,
            FuenteDato.tipo == "boletin_diario",
            FuenteDato.activa,
        )
    )
    fuente = fuente_result.scalar_one_or_none()
    if not fuente or not fuente.url_template:
        raise HTTPException(
            status_code=404,
            detail=f"No hay fuente de datos activa para jurisdiccion_id={req.jurisdiccion_id}",
        )

    # 2. Compute weekdays in the requested month
    _, days_in_month = _cal_module.monthrange(req.year, req.month)
    weekdays: List[str] = []
    for d in range(1, days_in_month + 1):
        dt = _date(req.year, req.month, d)
        if dt.weekday() < 5:  # Mon=0 … Fri=4
            weekdays.append(dt.strftime("%Y%m%d"))

    # 3. Fetch existing Boletines for this month+jurisdiccion
    prefix = f"{req.year}{str(req.month).zfill(2)}"
    existing_result = await db.execute(
        select(Boletin).where(
            Boletin.jurisdiccion_id == req.jurisdiccion_id,
            Boletin.filename.like(f"{prefix}%"),
        )
    )
    existing_by_filename: Dict[str, Any] = {b.filename: b for b in existing_result.scalars().all()}

    # 4. Upsert + queue each not-yet-completed section
    triggered = 0
    skipped = 0
    for day_str in weekdays:
        for section in req.sections:
            filename = f"{day_str}_{section}_Secc.pdf"
            boletin = existing_by_filename.get(filename)
            if boletin and boletin.status == "completed":
                skipped += 1
                continue
            source_url = build_url_from_template(fuente.url_template, filename)
            if boletin is None:
                boletin = Boletin(
                    filename=filename,
                    date=day_str,
                    section=section,
                    seccion_nombre=_PIPELINE_SECTION_NAMES.get(section),
                    status="extracting",
                    jurisdiccion_id=req.jurisdiccion_id,
                    source_url=source_url,
                )
                db.add(boletin)
                await db.flush()
            else:
                if not boletin.source_url:
                    boletin.source_url = source_url
                if not boletin.date:
                    boletin.date = day_str
                if not boletin.section:
                    boletin.section = section
                if not boletin.seccion_nombre:
                    boletin.seccion_nombre = _PIPELINE_SECTION_NAMES.get(section)
                boletin.status = "extracting"

            session_id = str(uuid.uuid4())[:8]
            background_tasks.add_task(
                _process_document_pipeline,
                boletin.id,
                filename,
                session_id,
                PipelineConfig(),
            )
            triggered += 1

    await db.commit()

    return {
        "success": True,
        "year": req.year,
        "month": req.month,
        "jurisdiccion_id": req.jurisdiccion_id,
        "triggered": triggered,
        "skipped_completed": skipped,
        "message": f"{triggered} secciones encoladas para procesamiento",
    }


@router.get("/status")
async def get_pipeline_status():
    """
    Get current pipeline status and statistics.
    
    Uses its own DB session to avoid cursor conflicts with background
    pipeline tasks that commit on the shared aiosqlite connection.
    """
    from app.db.database import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as db:
            # Single query: count boletines grouped by status
            result = await db.execute(
                select(Boletin.status, func.count()).group_by(Boletin.status)
            )
            rows = result.all()
            status_counts = {row[0]: row[1] for row in rows}
            total_boletines = sum(status_counts.values())
            
            # Ensure all expected keys exist
            for key in ["pending", "extracting", "chunking", "indexing", "completed", "failed"]:
                status_counts.setdefault(key, 0)
            
            # Total chunks
            chunks_result = await db.execute(select(func.count()).select_from(ChunkRecord))
            total_chunks = chunks_result.scalar() or 0
            
            # Total indexed (with indexed_at)
            indexed_result = await db.execute(
                select(func.count()).select_from(ChunkRecord).where(ChunkRecord.indexed_at.isnot(None))
            )
            total_indexed = indexed_result.scalar() or 0
        
        # Active session info (in-memory, no DB needed)
        active_session = None
        for sid, session in _active_sessions.items():
            if session.get("status") == "running":
                active_session = {"session_id": sid, **session}
                break
        
        return {
            "total_boletines": total_boletines,
            "by_status": status_counts,
            "total_chunks": total_chunks,
            "total_indexed": total_indexed,
            "active_session": active_session,
        }
    
    except Exception as e:
        logger.error(f"Error getting pipeline status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/defaults")
async def get_default_config():
    """
    Get default pipeline configuration.
    Useful for pre-populating the frontend config panel.
    """
    return PipelineConfig().model_dump()


# =============================================================================
# BACKGROUND PROCESSING FUNCTIONS
# =============================================================================

async def _process_document_pipeline(
    boletin_id: int,
    filename: str,
    session_id: str,
    config: PipelineConfig,
):
    """Background task: process a single document through the full pipeline."""
    from app.db.database import BackgroundSessionLocal
    
    TOTAL_STAGES = 7  # extract, clean, entity_mapping, chunk, index, analyze, completed
    
    # Track active session globally so /status can report it
    _active_sessions[session_id] = {
        "status": "running",
        "boletin_id": boletin_id,
        "filename": filename,
        "stage": "extracting",
        "stages_done": 0,
        "stages_total": TOTAL_STAGES,
    }
    
    async with BackgroundSessionLocal() as db:
        try:
            # Stage 1/7: EXTRACTION
            _active_sessions[session_id]["stage"] = "extracting"
            _active_sessions[session_id]["stages_done"] = 0
            await _emit_stage(session_id, boletin_id, filename, "extracting", 1, TOTAL_STAGES)
            await _update_status(db, boletin_id, "extracting")

            text = await _extract_text(boletin_id, filename, config.extraction, db)

            # Stage 1.5: SUMARIO PARSING (solo boletines provinciales de Córdoba)
            await _parse_and_store_sumario(db, boletin_id, filename, text)

            # Stage 2/7: CLEANING
            _active_sessions[session_id]["stage"] = "cleaning"
            _active_sessions[session_id]["stages_done"] = 1
            await _emit_stage(session_id, boletin_id, filename, "cleaning", 2, TOTAL_STAGES)

            if config.cleaning.enabled:
                text = _clean_text(text, config.cleaning)

            # Stage 3/7: ENTITY_MAPPING
            _active_sessions[session_id]["stage"] = "entity_mapping"
            _active_sessions[session_id]["stages_done"] = 2
            await _emit_stage(session_id, boletin_id, filename, "entity_mapping", 3, TOTAL_STAGES)
            from app.services.entity_service import get_entity_service
            entity_service = get_entity_service()
            pre_entities, entity_map = await _build_entity_map(session_id, boletin_id, text, entity_service)

            # Persist entities + relationships to PostgreSQL and Neo4j (dual-write)
            try:
                await entity_service.persist_entities(pre_entities, boletin_id, db)
                relationships = entity_service.detect_relationships(pre_entities, text)
                await entity_service.persist_relationships(relationships, boletin_id, pre_entities, db)
            except Exception as _ep:
                logger.warning("Entity persistence failed (non-fatal): %s", _ep)

            # Stage 4/7: CHUNKING
            _active_sessions[session_id]["stage"] = "chunking"
            _active_sessions[session_id]["stages_done"] = 3
            await _emit_stage(session_id, boletin_id, filename, "chunking", 4, TOTAL_STAGES)
            await _update_status(db, boletin_id, "chunking")

            chunks = _chunk_text(text, config.chunking, entity_map=entity_map)

            # Stage 5/7: ENRICHMENT + INDEXING
            _active_sessions[session_id]["stage"] = "indexing"
            _active_sessions[session_id]["stages_done"] = 4
            await _emit_stage(session_id, boletin_id, filename, "indexing", 5, TOTAL_STAGES,
                            details={"chunks_created": len(chunks)})
            await _update_status(db, boletin_id, "indexing")

            async with _sqlite_write_lock:
                indexed = await _index_chunks(
                    db, boletin_id, filename, chunks, config.enrichment, config.indexing
                )

            # Stage 6/7: GEMINI ANALYSIS + ADVERSARIAL VERIFICATION
            _active_sessions[session_id]["stage"] = "analyzing"
            _active_sessions[session_id]["stages_done"] = 5
            await _emit_stage(session_id, boletin_id, filename, "analyzing", 6, TOTAL_STAGES,
                            details={"chunks_indexed": indexed})
            await _update_status(db, boletin_id, "analyzing")

            # Lock is managed inside _analyze_document — only the DB writes are
            # serialised; the Gemini API call runs concurrently across sections.
            actos_count = await _analyze_document(db, boletin_id, filename, text)

            # Stage 6b: ENRIQUECIMIENTO POST-ANÁLISIS (non-fatal)
            try:
                _actos_para_enriquecer = await _get_actos_for_enrichment(db, boletin_id)
                if _actos_para_enriquecer:
                    _enrich_stats = await _enrich_entities_from_actos(
                        db, boletin_id, _actos_para_enriquecer, entity_service
                    )
                    logger.info(
                        "[%s] Post-analysis enrichment: +%d entidades, +%d relaciones",
                        session_id,
                        _enrich_stats.get("entities_created", 0),
                        _enrich_stats.get("relationships_created", 0),
                    )
            except Exception as _enrich_exc:
                logger.warning("[%s] Post-analysis enrichment falló (non-fatal): %s", session_id, _enrich_exc)

            # Stage 7/7: COMPLETED
            _active_sessions[session_id]["stage"] = "completed"
            _active_sessions[session_id]["stages_done"] = 7
            _active_sessions[session_id]["status"] = "completed"
            await _update_status(db, boletin_id, "completed")
            await _emit_stage(session_id, boletin_id, filename, "completed", 7, TOTAL_STAGES,
                            details={"chunks_created": len(chunks), "chunks_indexed": indexed, "actos_extracted": actos_count})
            
            await event_bus.emit(
                EventType.PIPELINE_DOCUMENT_COMPLETED,
                data={
                    "session_id": session_id,
                    "boletin_id": boletin_id,
                    "filename": filename,
                    "chunks_created": len(chunks),
                    "chunks_indexed": indexed,
                    "actos_extracted": actos_count,
                },
                source="pipeline"
            )
            
            logger.info(f"Document {boletin_id} processed: {len(chunks)} chunks, {indexed} indexed")
            
            # Emit pipeline completed for single-doc processing
            await event_bus.emit(
                EventType.PIPELINE_COMPLETED,
                data={
                    "session_id": session_id,
                    "total": 1,
                    "completed": 1,
                    "failed": 0,
                },
                source="pipeline"
            )
            
            # Clean up session after a delay (let frontend poll it)
            _active_sessions.pop(session_id, None)
        
        except Exception as e:
            logger.error(f"Pipeline failed for {boletin_id}: {e}", exc_info=True)
            _active_sessions[session_id] = {
                "status": "failed",
                "boletin_id": boletin_id,
                "filename": filename,
                "error": str(e),
                "stages_done": _active_sessions.get(session_id, {}).get("stages_done", 0),
                "stages_total": TOTAL_STAGES,
            }
            await _update_status(db, boletin_id, "failed", str(e))
            
            await event_bus.emit(
                EventType.PIPELINE_DOCUMENT_FAILED,
                data={
                    "session_id": session_id,
                    "boletin_id": boletin_id,
                    "filename": filename,
                    "error": str(e),
                },
                source="pipeline"
            )
            
            # Emit pipeline completed (with failure) for single-doc processing
            await event_bus.emit(
                EventType.PIPELINE_COMPLETED,
                data={
                    "session_id": session_id,
                    "total": 1,
                    "completed": 0,
                    "failed": 1,
                },
                source="pipeline"
            )
            
            _active_sessions.pop(session_id, None)


async def _process_all_pipeline(
    boletin_list: List[Dict[str, Any]],
    session_id: str,
    config: PipelineConfig,
):
    """Background task: process all pending documents sequentially."""
    total = len(boletin_list)
    completed = 0
    failed = 0
    
    for i, item in enumerate(boletin_list):
        boletin_id = item["id"]
        filename = item["filename"]
        
        # Update session tracking
        if session_id in _active_sessions:
            _active_sessions[session_id]["current"] = i + 1
        
        # Emit progress
        await event_bus.emit(
            EventType.PIPELINE_DOCUMENT_STARTED,
            data={
                "session_id": session_id,
                "boletin_id": boletin_id,
                "filename": filename,
                "progress": {"current": i + 1, "total": total},
            },
            source="pipeline"
        )
        
        try:
            await _process_document_pipeline(boletin_id, filename, session_id, config)
            completed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Batch: document {boletin_id} failed: {e}")
            if session_id in _active_sessions:
                _active_sessions[session_id]["errors"].append({
                    "boletin_id": boletin_id,
                    "filename": filename,
                    "error": str(e),
                })
    
    # Mark session as complete
    if session_id in _active_sessions:
        _active_sessions[session_id]["status"] = "completed"
    
    # Emit pipeline completed
    await event_bus.emit(
        EventType.PIPELINE_COMPLETED,
        data={
            "session_id": session_id,
            "total": total,
            "completed": completed,
            "failed": failed,
        },
        source="pipeline"
    )
    
    logger.info(f"Batch pipeline {session_id} complete: {completed}/{total} successful, {failed} failed")
    _active_sessions.pop(session_id, None)


# =============================================================================
# PIPELINE STAGE HELPERS
# =============================================================================

def _find_pdf(filename: str) -> Optional[Path]:
    """
    Find a PDF file across all known directories.
    
    Search order:
    1. boletines/{year}/{month}/ - main download location (organized by date)
    2. data/raw/ - legacy flat directory
    3. data/uploaded_documents/ - manual uploads
    """
    # 1. Search in boletines/{year}/{month}/ based on filename pattern YYYYMMDD_*
    if settings.BOLETINES_DIR.exists() and len(filename) >= 8:
        try:
            year = filename[:4]
            month = filename[4:6]
            candidate = settings.BOLETINES_DIR / year / month / filename
            if candidate.exists():
                return candidate
        except (ValueError, IndexError):
            pass
        
        # Fallback: glob search in boletines tree
        matches = list(settings.BOLETINES_DIR.rglob(filename))
        if matches:
            return matches[0]
    
    # 2. Search in uploads/{year}/{month}/ (uploaded via API)
    if settings.UPLOADS_DIR.exists() and len(filename) >= 8:
        try:
            year = filename[:4]
            month = filename[4:6]
            candidate = settings.UPLOADS_DIR / year / month / filename
            if candidate.exists():
                return candidate
        except (ValueError, IndexError):
            pass

        matches = list(settings.UPLOADS_DIR.rglob(filename))
        if matches:
            return matches[0]

    # 3. Flat directories (legacy)
    for search_dir in [
        settings.DATA_DIR / "raw",
        settings.DATA_DIR / "uploaded_documents",
        settings.DATA_DIR / "pdfs",
    ]:
        candidate = search_dir / filename
        if candidate.exists():
            return candidate
    
    return None


async def _emit_stage(
    session_id: str, 
    boletin_id: int, 
    filename: str, 
    stage: str,
    current: int,
    total: int,
    details: Optional[Dict] = None,
):
    """Emit a pipeline stage event via EventBus."""
    await event_bus.emit(
        EventType.PIPELINE_DOCUMENT_STAGE,
        data={
            "session_id": session_id,
            "boletin_id": boletin_id,
            "filename": filename,
            "stage": stage,
            "progress": {"current": current, "total": total},
            "details": details or {},
        },
        source="pipeline"
    )


async def _update_status(db: AsyncSession, boletin_id: int, status: str, error: str = None):
    """Update boletin status in database. Handles stale session gracefully."""
    try:
        values = {"status": status}
        if error:
            values["error_message"] = error
        await db.execute(update(Boletin).where(Boletin.id == boletin_id).values(**values))
        await db.commit()
    except Exception as e:
        logger.warning(f"_update_status failed for {boletin_id} -> {status}: {e}")
        try:
            await db.rollback()
            # Retry once after rollback
            values = {"status": status}
            if error:
                values["error_message"] = error
            await db.execute(update(Boletin).where(Boletin.id == boletin_id).values(**values))
            await db.commit()
        except Exception as retry_err:
            logger.error(f"_update_status retry also failed for {boletin_id}: {retry_err}")
            try:
                await db.rollback()
            except Exception:
                pass


async def _extract_text(
    boletin_id: int,
    filename: str,
    config: ExtractionConfig,
    db: AsyncSession,
) -> str:
    """
    Extrae texto de un boletín usando la siguiente jerarquía de fuentes:

    1. .txt cacheado en data/processed/ (más rápido, evita re-extracción)
    2. PDF local en boletines/ o uploads/ (pipeline clásico)
    3. URL remota (Opción A: URL-first, sin almacenar PDF en disco)

    Cuando se usa la URL, el PDF se descarga a un tempfile, se extrae el texto,
    y el tempfile se elimina. Solo el .txt queda guardado en disco.
    """
    # 1. .txt cacheado
    txt_filename = filename.replace(".pdf", ".txt")
    txt_path = settings.DATA_DIR / "processed" / txt_filename

    if txt_path.exists():
        logger.info(f"Reading existing text file: {txt_path}")
        return txt_path.read_text(encoding="utf-8", errors="replace")

    # 2. PDF local
    pdf_path = _find_pdf(filename)

    if pdf_path:
        from app.services.extractors.registry import ExtractorRegistry
        content = await ExtractorRegistry.extract(pdf_path, method=config.extractor)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(content.full_text, encoding="utf-8")
        return content.full_text

    # 3. URL remota (Opción A)
    source_url = await _get_source_url(boletin_id, filename, db)
    if not source_url:
        raise FileNotFoundError(
            f"No se encontró PDF local ni URL de origen para {filename}"
        )

    logger.info(f"[Option A] Extrayendo desde URL: {source_url}")
    from app.services.url_fetcher import fetch_and_extract_text
    text = await fetch_and_extract_text(source_url, extractor_method=config.extractor)

    # Guardar .txt para evitar re-descarga en futuros reprocesos
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(text, encoding="utf-8")
    logger.info(f"[Option A] Texto guardado en {txt_path} ({len(text)} chars)")

    return text


async def _get_source_url(
    boletin_id: int,
    filename: str,
    db: AsyncSession,
) -> Optional[str]:
    """
    Resuelve la URL de origen de un boletín.

    Orden de búsqueda:
    1. Boletin.source_url (guardada en DB en el momento del registro)
    2. Construir desde JurisdiccionSyncConfig.source_url_template
    """
    from sqlalchemy import select
    from app.db.models import Boletin, JurisdiccionSyncConfig

    # 1. URL ya guardada en el registro del boletín
    result = await db.execute(
        select(Boletin.source_url, Boletin.jurisdiccion_id)
        .where(Boletin.id == boletin_id)
    )
    row = result.first()
    if row and row.source_url:
        return row.source_url

    # 2. Construir desde template de la jurisdicción
    if row and row.jurisdiccion_id:
        cfg_result = await db.execute(
            select(JurisdiccionSyncConfig.source_url_template)
            .where(JurisdiccionSyncConfig.jurisdiccion_id == row.jurisdiccion_id)
        )
        cfg_row = cfg_result.first()
        if cfg_row and cfg_row.source_url_template:
            from app.services.url_fetcher import build_url_from_template
            return build_url_from_template(cfg_row.source_url_template, filename)

    return None


async def _parse_and_store_sumario(
    db: AsyncSession,
    boletin_id: int,
    filename: str,
    text: str,
) -> None:
    """
    Parsea el sumario del boletín y lo persiste en sumarios_parseados.
    Solo actúa sobre boletines provinciales de Córdoba (fuente=PROVINCIAL, jurisdiccion_id=1).
    No-bloqueante: cualquier fallo se loguea como warning sin interrumpir el pipeline.
    """
    import json
    try:
        from sqlalchemy import select
        from app.db.models import Boletin, FuenteBoletin, SumarioParseado
        from app.services.sumario_parser import SumarioParser

        # Verificar que es un boletín provincial de Córdoba
        result = await db.execute(
            select(Boletin.fuente, Boletin.jurisdiccion_id).where(Boletin.id == boletin_id)
        )
        row = result.first()
        if not row or row.fuente != FuenteBoletin.PROVINCIAL or row.jurisdiccion_id != 1:
            return

        # Skip si ya tiene sumario parseado
        existing = await db.execute(
            select(SumarioParseado.id).where(SumarioParseado.boletin_id == boletin_id)
        )
        if existing.first():
            return

        sumario = SumarioParser().parse_from_text(text)

        record = SumarioParseado(
            boletin_id=boletin_id,
            format_type=sumario.format_type,
            confidence=sumario.confidence,
            pagina_sumario=sumario.sumario_page,
            entries_json=json.dumps([e.__dict__ for e in sumario.entries], ensure_ascii=False),
            raw_text=sumario.raw_text if sumario.found else None,
        )
        db.add(record)
        await db.commit()

        logger.info(
            "[pipeline] Sumario boletin_id=%d: found=%s format=%s entries=%d confianza=%.2f",
            boletin_id, sumario.found, sumario.format_type, len(sumario.entries), sumario.confidence
        )
    except Exception as exc:
        logger.warning("[pipeline] Sumario parsing no-fatal error boletin_id=%d: %s", boletin_id, exc)


def _clean_text(text: str, config) -> str:
    """Clean extracted text using TextCleaner."""
    from app.services.text_cleaner import TextCleaner, CleaningConfig
    
    cleaner_config = CleaningConfig(
        fix_encoding=config.fix_encoding,
        normalize_unicode=config.normalize_unicode,
        normalize_whitespace=config.normalize_whitespace,
        remove_artifacts=config.remove_artifacts,
        normalize_legal_text=config.normalize_legal_text,
    )
    cleaner = TextCleaner(config=cleaner_config)
    return cleaner.clean(text)


def _chunk_text(text: str, config, entity_map=None) -> list:
    """Chunk text using ChunkingService."""
    from app.services.chunking_service import ChunkingService, ChunkingConfig

    chunking_config = ChunkingConfig(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        min_chunk_size=config.min_chunk_size,
        strategy=config.strategy,
    )
    service = ChunkingService(config=chunking_config)
    return service.chunk(text, config=chunking_config, entity_map=entity_map)


async def _build_entity_map(
    session_id: str, boletin_id: int, cleaned_text: str, entity_service
):
    """Pre-scan entities before chunking to build spatial EntityMap."""
    try:
        entities = entity_service.extract_entities(cleaned_text)
        entity_map = entity_service.build_entity_map(entities, cleaned_text)
        logger.info(f"[{session_id}] Entity pre-scan: {len(entities)} entities mapped")
        return entities, entity_map
    except Exception as e:
        logger.warning(f"[{session_id}] Entity pre-scan failed (non-fatal): {e}")
        return [], None


async def _index_chunks(
    db: AsyncSession,
    boletin_id: int,
    filename: str,
    chunks: list,
    enrichment_config: EnrichmentConfig,
    indexing_config: IndexingConfig,
) -> int:
    """Index chunks into SQLite (+ FTS5) and optionally ChromaDB."""
    from datetime import datetime
    import hashlib
    
    from sqlalchemy.exc import IntegrityError, OperationalError

    document_id = filename.replace(".pdf", "").replace(".txt", "")
    indexed_count = 0

    # Remove existing chunks to avoid UNIQUE constraint violations on re-processing.
    # Wrapped in try/except: if the DB is locked, roll back and continue — the
    # on_conflict_do_nothing inserts below will silently skip existing rows.
    try:
        count_result = await db.execute(
            select(func.count()).select_from(ChunkRecord).where(
                ChunkRecord.document_id == document_id
            )
        )
        existing_count = count_result.scalar() or 0
        if existing_count > 0:
            logger.info(
                "Re-indexing %s: removing %d existing chunks first",
                document_id, existing_count
            )
            await db.execute(
                delete(ChunkRecord).where(ChunkRecord.document_id == document_id)
            )
            await db.commit()
    except (IntegrityError, OperationalError) as cleanup_err:
        logger.warning(
            "Cleanup failed for %s (%s). Proceeding — inserts will skip duplicates.",
            document_id, cleanup_err,
        )
        await db.rollback()

    # Dialect-specific insert for on_conflict_do_nothing support
    if settings.is_postgres:
        from sqlalchemy.dialects.postgresql import insert as _dialect_insert
    else:
        from sqlalchemy.dialects.sqlite import insert as _dialect_insert

    # Optional enricher
    enricher = None
    if enrichment_config.enabled:
        try:
            from app.services.chunk_enricher import ChunkEnricher
            enricher = ChunkEnricher()
        except Exception as e:
            logger.warning(f"ChunkEnricher unavailable: {e}")
    
    # Optional embedding service
    embedding_service = None
    if indexing_config.use_chromadb:
        try:
            from app.services.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
        except Exception as e:
            logger.warning(f"EmbeddingService unavailable: {e}")
    
    COMMIT_BATCH_SIZE = 10  # Commit every N chunks to avoid long-held write locks
    
    for chunk in chunks:
        try:
            chunk_hash = hashlib.sha256(chunk.text.encode()).hexdigest()
            
            # Enrich
            enrichment = {}
            if enricher:
                anchored_entities = chunk.entity_anchors if hasattr(chunk, "entity_anchors") else None
                enrichment = enricher.enrich(
                    chunk_text=chunk.text,
                    chunk_index=chunk.chunk_index,
                    document_id=document_id,
                    context={
                        "boletin_id": boletin_id,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    },
                    anchored_entities=anchored_entities,
                )
            
            # Insert ChunkRecord using on_conflict_do_nothing to safely handle
            # duplicates when cleanup was skipped due to a locked database.
            if indexing_config.use_sqlite:
                stmt = _dialect_insert(ChunkRecord).values(
                    document_id=document_id,
                    boletin_id=boletin_id,
                    chunk_index=chunk.chunk_index,
                    chunk_hash=chunk_hash,
                    text=chunk.text,
                    num_chars=chunk.num_chars,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    section_type=enrichment.get("section_type"),
                    topic=enrichment.get("topic"),
                    language="es",
                    has_tables=enrichment.get("has_tables", False),
                    has_amounts=enrichment.get("has_amounts", False),
                    entities_json=enrichment.get("entities_json"),
                    embedding_model=indexing_config.embedding_model if indexing_config.use_chromadb else None,
                    embedding_dimensions=3072 if indexing_config.use_chromadb else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ).on_conflict_do_nothing(
                    index_elements=["document_id", "chunk_index"]
                )
                await db.execute(stmt)
            
            # Index in ChromaDB
            if indexing_config.use_chromadb and embedding_service and embedding_service.collection:
                try:
                    chunk_id = f"{document_id}_chunk_{chunk.chunk_index}"
                    embedding_service.collection.add(
                        documents=[chunk.text],
                        ids=[chunk_id],
                        metadatas=[{
                            "document_id": document_id,
                            "boletin_id": str(boletin_id),
                            "chunk_index": chunk.chunk_index,
                            "section_type": enrichment.get("section_type", "unknown"),
                            "filename": filename,
                        }],
                    )
                    
                except Exception as e:
                    logger.warning(f"ChromaDB indexing failed for chunk {chunk.chunk_index}: {e}")
            
            indexed_count += 1
            
            # Periodic commit to release write lock and let HTTP readers through
            if indexed_count % COMMIT_BATCH_SIZE == 0:
                await db.commit()
        
        except Exception as e:
            logger.error(f"Failed to index chunk {chunk.chunk_index} of {filename}: {e}")
    
    # Final commit for remaining chunks
    await db.commit()
    return indexed_count


async def _analyze_document(
    db: AsyncSession,
    boletin_id: int,
    filename: str,
    text: str,
) -> int:
    """
    Run Gemini analysis on extracted text and save individual actos to the database.

    Phases wired here:
    - Phase I/IV: WatcherService singleton (avoids re-loading the Gemini model).
    - Phase II: AIUService singleton decomposes each acto into AIUs.
    - Phase IV: ReferenceFirewallService validates references per acto (per-request
      so it uses the live DB session; fts_service=None is safe — acto-ref lookups
      fall through to UNVERIFIABLE via internal try/except).
    - Phase V: record_vcp() emits VCP metrics for the ObservabilityManager.

    Returns the number of actos saved.
    """
    import time
    from app.db.crud import create_analisis
    from app.services.reference_firewall import ReferenceFirewallService
    from app.core.observability import record_vcp

    # BUG-1: use singletons instead of fresh WatcherService() each call
    try:
        watcher, aiu_service = await _get_watcher_and_aiu()
    except Exception as _e:
        logger.warning("Análisis Gemini no disponible (%s) — etapa omitida", _e)
        return 0

    # Per-request firewall wired with current db session and fts_service
    try:
        from app.services.fts_service import get_fts_service
        _fts_svc = get_fts_service()
    except Exception:
        _fts_svc = None
    firewall = ReferenceFirewallService(db, _fts_svc)

    # Build metadata for contextual prompt
    metadata = {
        "boletin": filename.replace(".pdf", ""),
    }

    # Try to get jurisdiccion info from the boletin record
    try:
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(Boletin).options(selectinload(Boletin.jurisdiccion)).where(Boletin.id == boletin_id)
        )
        boletin = result.scalar_one_or_none()
        if boletin:
            if boletin.jurisdiccion:
                metadata["jurisdiccion_nombre"] = boletin.jurisdiccion.nombre
            metadata["fuente"] = getattr(boletin, "fuente", "provincial")
            metadata["section_type"] = str(boletin.section) if boletin.section else ""
            seccion_nombre = getattr(boletin, "seccion_nombre", None)
            if seccion_nombre:
                metadata["seccion_nombre"] = seccion_nombre
    except Exception as e:
        logger.warning(f"Could not load boletin metadata for analysis: {e}")

    # Run Gemini analysis
    try:
        actos = await watcher.analyze_content(content=text, metadata=metadata)
    except Exception as e:
        logger.error(f"Gemini analysis failed for {filename}: {e}")
        return 0

    # Adversarial pipeline (Fases II, III, IV) — run concurrently across sections.
    # DB writes happen AFTER all computation, under the write lock.
    t_start = time.monotonic()
    total_aius = 0
    vcp_results: List[Any] = []

    from agents.verification.agent import VerificationAgent
    try:
        from app.services.retrieval_service import get_retrieval_service
        _retrieval_svc = get_retrieval_service()
    except Exception:
        _retrieval_svc = None
    verifier = VerificationAgent(retrieval_service=_retrieval_svc, firewall_service=firewall)

    # Phase 1: compute — Gemini results + adversarial pipeline (no DB writes here)
    prepared: List[Dict[str, Any]] = []
    for acto in actos:
        try:
            fragment_text = acto.pop("_fragment_content", text[:500])
            acto.pop("_fragment_index", None)
            acto.pop("_resumen_fragmento", None)
            acto.pop("_model_used", None)

            # Phase IV: firewall (DB reads only)
            fw_result = None
            try:
                fw_result = await firewall.validate_references(fragment_text)
            except Exception as fw_e:
                logger.debug(f"Firewall skipped for {filename}: {fw_e}")

            # Phase II: AIU decomposition (pure computation)
            aiu_result = None
            aiu_summary = None
            try:
                aiu_result = aiu_service.decompose_actos([acto])
                total_aius += aiu_result.total_aius
            except Exception as aiu_e:
                logger.debug(f"AIU decomposition skipped for {filename}: {aiu_e}")

            # Phase III: Adversarial Verification (DB reads only)
            verification_result = None
            if aiu_result is not None and aiu_result.total_aius > 0:
                try:
                    verification_result = await verifier.verify_aius(
                        aiu_result.aius, boletin_id=boletin_id
                    )
                    vcp_results.append(verification_result)
                    aiu_summary = {
                        "total_aius": verification_result.total_aius,
                        "verified": verification_result.verified,
                        "unverifiable": verification_result.unverifiable,
                        "contradicted": verification_result.contradicted,
                        "vcp_score": verification_result.vcp_score,
                        "requires_human_review": verification_result.requires_human_review,
                        "by_type": aiu_result.by_type,
                    }
                except Exception as ve:
                    logger.debug(f"VerificationAgent skipped for {filename}: {ve}")
                    aiu_summary = {
                        "total_aius": aiu_result.total_aius,
                        "by_type": aiu_result.by_type,
                    }
            elif aiu_result is not None:
                aiu_summary = {
                    "total_aius": aiu_result.total_aius,
                    "by_type": aiu_result.by_type,
                }

            firewall_score = None
            if fw_result is not None:
                firewall_score = fw_result.firewall_score
            if verification_result is not None:
                firewall_score = verification_result.vcp_score

            prepared.append({
                "acto": acto,
                "fragment_text": fragment_text,
                "aiu_summary": aiu_summary,
                "firewall_score": firewall_score,
            })
        except Exception as e:
            logger.error(f"Failed to prepare acto for {filename}: {e}")

    # Phase 2: save — serialised so concurrent sections never write simultaneously
    total_saved = 0
    async with _sqlite_write_lock:
        for item in prepared:
            try:
                db_analisis = await create_analisis(
                    db,
                    boletin_id=boletin_id,
                    fragmento=item["fragment_text"],
                    analisis_data=item["acto"],
                )
                if item["aiu_summary"] is not None:
                    db_analisis.aiu_summary_json = item["aiu_summary"]
                if item["firewall_score"] is not None:
                    db_analisis.firewall_score = item["firewall_score"]
                total_saved += 1
            except Exception as e:
                logger.error(f"Failed to save acto for {filename}: {e}")
        await db.commit()

    # Emit VCP metrics using real VerificationAgent data
    if total_saved > 0:
        if vcp_results:
            total_verified = sum(vr.verified for vr in vcp_results)
            total_unverifiable = sum(vr.unverifiable for vr in vcp_results)
            total_contradicted = sum(vr.contradicted for vr in vcp_results)
            avg_vcp = sum(vr.vcp_score for vr in vcp_results) / len(vcp_results)
        else:
            total_verified = 0
            total_unverifiable = total_aius
            total_contradicted = 0
            avg_vcp = 1.0
        latency_ms = (time.monotonic() - t_start) * 1000
        record_vcp(
            vcp_score=avg_vcp,
            total_aius=total_aius,
            verified=total_verified,
            unverifiable=total_unverifiable,
            contradicted=total_contradicted,
            boletin_id=boletin_id,
            latency_ms=latency_ms,
        )

    logger.info(f"Analysis complete for {filename}: {total_saved} actos saved")
    return total_saved


async def _get_actos_for_enrichment(db: AsyncSession, boletin_id: int) -> list:
    """Devuelve los actos Gemini guardados como dicts para enriquecimiento post-análisis."""
    from app.db.crud import get_analisis_by_boletin
    rows = await get_analisis_by_boletin(db, boletin_id, skip=0, limit=500)
    out = []
    for row in rows:
        extra = row.datos_extra or {}
        out.append({
            "organismo":     row.organismo or "",
            "beneficiarios": row.beneficiarios_json or [],
            "tipo_acto":     row.tipo_acto or "otro",
            "descripcion":   row.descripcion or "",
            "firmante":      extra.get("firmante", "") if isinstance(extra, dict) else "",
        })
    return out


async def _enrich_entities_from_actos(
    db: AsyncSession,
    boletin_id: int,
    actos: list,
    entity_svc,
) -> dict:
    """
    Crea entidades y relaciones adicionales a partir de los actos estructurados de Gemini.
    Retroalimenta el grafo con datos de alta precisión extraídos por el LLM.
    """
    from app.services.entity_service import EntityResult, RelationshipResult

    created_entities = 0
    created_rels = 0

    for acto in actos:
        org_nombre = (acto.get("organismo") or "").strip()
        tipo_acto = acto.get("tipo_acto", "otro")
        beneficiarios = acto.get("beneficiarios") or []
        firmante = (acto.get("firmante") or "").strip()

        new_entities: list = []

        # Organismo como entidad
        if org_nombre and len(org_nombre) >= 5:
            new_entities.append(EntityResult(
                tipo="organismo",
                nombre=org_nombre,
                nombre_normalizado=entity_svc.normalize_entity(org_nombre, "organismo"),
                confianza=0.95,
                posicion=0,
                metadata={},
            ))

        # Beneficiarios (personas o empresas)
        for benef in beneficiarios:
            nombre = (benef if isinstance(benef, str) else str(benef)).strip()
            if not nombre or len(nombre) < 4:
                continue
            # Heurística: ALL-CAPS con sufijo societario → empresa, sino → persona
            import re as _re
            if _re.search(r'S\.A\.|S\.R\.L\.|S\.A\.S\.|COOPERATIVA|CONSORCIO|FUNDACI', nombre, _re.IGNORECASE):
                tipo_e = "empresa"
            else:
                tipo_e = "persona"
            new_entities.append(EntityResult(
                tipo=tipo_e,
                nombre=nombre,
                nombre_normalizado=entity_svc.normalize_entity(nombre, tipo_e),
                confianza=0.90,
                posicion=0,
                metadata={},
            ))

        # Firmante como persona
        if firmante and len(firmante) >= 5:
            new_entities.append(EntityResult(
                tipo="persona",
                nombre=firmante,
                nombre_normalizado=entity_svc.normalize_entity(firmante, "persona"),
                confianza=0.90,
                posicion=0,
                metadata={},
            ))

        if new_entities:
            stats = await entity_svc.persist_entities(new_entities, boletin_id, db)
            created_entities += stats.get("created", 0)

        # Relaciones organismo → beneficiario
        if org_nombre and beneficiarios:
            tipo_rel_map = {
                "designacion": "designa",
                "contratacion": "contrata",
                "subsidio": "recibe_subsidio",
                "adjudicacion": "adjudica",
            }
            tipo_rel = "se_relaciona_con"
            for k, v in tipo_rel_map.items():
                if k in tipo_acto.lower():
                    tipo_rel = v
                    break

            rels: list = []
            for benef in beneficiarios:
                nombre = (benef if isinstance(benef, str) else str(benef)).strip()
                if nombre and len(nombre) >= 4:
                    rels.append(RelationshipResult(
                        entidad_origen=org_nombre,
                        entidad_destino=nombre,
                        tipo_relacion=tipo_rel,
                        contexto=(acto.get("descripcion") or "")[:300],
                        confianza=0.90,
                        metadata={},
                    ))

            if rels:
                n = await entity_svc.persist_relationships(rels, boletin_id, new_entities, db)
                created_rels += n

    return {"entities_created": created_entities, "relationships_created": created_rels}
