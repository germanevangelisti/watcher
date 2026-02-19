"""
Pipeline endpoints - Unified document processing pipeline

Provides endpoints for:
- Resetting all processed data (total and per document)
- Processing single documents through the complete pipeline
- Batch processing all pending documents
- Checking pipeline status and statistics
- Getting default pipeline configuration
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete

from app.db.session import get_db
from app.db.models import Boletin, ChunkRecord, Analisis
from app.core.config import settings
from app.core.events import event_bus, EventType
from app.schemas.pipeline import (
    PipelineResponse,
    PipelineStage,
    StageStats,
    PipelineConfig,
    ExtractionConfig,
    CleaningConfig as PipelineCleaningConfig,
    ChunkingConfigSchema,
    EnrichmentConfig,
    IndexingConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory session tracking for active pipeline runs
_active_sessions: Dict[str, Dict[str, Any]] = {}


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
    
    TOTAL_STAGES = 6  # extract, clean, chunk, index, analyze, completed
    
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
            # Stage 1/6: EXTRACTION
            _active_sessions[session_id]["stage"] = "extracting"
            _active_sessions[session_id]["stages_done"] = 0
            await _emit_stage(session_id, boletin_id, filename, "extracting", 1, TOTAL_STAGES)
            await _update_status(db, boletin_id, "extracting")
            
            text = await _extract_text(boletin_id, filename, config.extraction, db)
            
            # Stage 2/6: CLEANING
            _active_sessions[session_id]["stage"] = "cleaning"
            _active_sessions[session_id]["stages_done"] = 1
            await _emit_stage(session_id, boletin_id, filename, "cleaning", 2, TOTAL_STAGES)
            
            if config.cleaning.enabled:
                text = _clean_text(text, config.cleaning)
            
            # Stage 3/6: CHUNKING
            _active_sessions[session_id]["stage"] = "chunking"
            _active_sessions[session_id]["stages_done"] = 2
            await _emit_stage(session_id, boletin_id, filename, "chunking", 3, TOTAL_STAGES)
            await _update_status(db, boletin_id, "chunking")
            
            chunks = _chunk_text(text, config.chunking)
            
            # Stage 4/6: ENRICHMENT + INDEXING
            _active_sessions[session_id]["stage"] = "indexing"
            _active_sessions[session_id]["stages_done"] = 3
            await _emit_stage(session_id, boletin_id, filename, "indexing", 4, TOTAL_STAGES, 
                            details={"chunks_created": len(chunks)})
            await _update_status(db, boletin_id, "indexing")
            
            indexed = await _index_chunks(
                db, boletin_id, filename, chunks, config.enrichment, config.indexing
            )
            
            # Stage 5/6: GEMINI ANALYSIS
            _active_sessions[session_id]["stage"] = "analyzing"
            _active_sessions[session_id]["stages_done"] = 4
            await _emit_stage(session_id, boletin_id, filename, "analyzing", 5, TOTAL_STAGES,
                            details={"chunks_indexed": indexed})
            await _update_status(db, boletin_id, "analyzing")
            
            actos_count = await _analyze_document(db, boletin_id, filename, text)
            
            # Stage 6/6: COMPLETED
            _active_sessions[session_id]["stage"] = "completed"
            _active_sessions[session_id]["stages_done"] = 6
            _active_sessions[session_id]["status"] = "completed"
            await _update_status(db, boletin_id, "completed")
            await _emit_stage(session_id, boletin_id, filename, "completed", 6, TOTAL_STAGES,
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
    
    # 2. Flat directories
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
    """Extract text from PDF or read existing .txt file."""
    # Check for existing .txt first
    txt_filename = filename.replace(".pdf", ".txt")
    txt_path = settings.DATA_DIR / "processed" / txt_filename
    
    if txt_path.exists():
        logger.info(f"Reading existing text file: {txt_path}")
        return txt_path.read_text(encoding="utf-8", errors="replace")
    
    # Extract from PDF - search all known directories
    pdf_path = _find_pdf(filename)
    
    
    if not pdf_path:
        raise FileNotFoundError(f"No PDF or text file found for {filename}")
    
    # Use ExtractorRegistry
    from app.services.extractors.registry import ExtractorRegistry
    content = await ExtractorRegistry.extract(pdf_path, method=config.extractor)
    
    # Save the extracted text
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(content.full_text, encoding="utf-8")
    
    return content.full_text


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


def _chunk_text(text: str, config) -> list:
    """Chunk text using ChunkingService."""
    from app.services.chunking_service import ChunkingService, ChunkingConfig
    
    chunking_config = ChunkingConfig(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        min_chunk_size=config.min_chunk_size,
        strategy=config.strategy,
    )
    service = ChunkingService(config=chunking_config)
    return service.chunk(text, config=chunking_config)


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
    
    document_id = filename.replace(".pdf", "").replace(".txt", "")
    indexed_count = 0
    
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
                enrichment = enricher.enrich(
                    chunk_text=chunk.text,
                    chunk_index=chunk.chunk_index,
                    document_id=document_id,
                    context={
                        "boletin_id": boletin_id,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    },
                )
            
            # Create ChunkRecord in SQLite
            record = None
            if indexing_config.use_sqlite:
                record = ChunkRecord(
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
                )
                db.add(record)
            
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
                    
                    # Update indexed_at
                    if record is not None:
                        record.indexed_at = datetime.utcnow()
                    
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
    
    Returns the number of actos extracted.
    """
    from app.services.watcher_service import WatcherService
    from app.db.crud import create_analisis
    
    watcher = WatcherService()
    
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
            # Pass readable section name for better contextual prompt
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
    
    # Save each acto individually
    total_saved = 0
    for acto in actos:
        try:
            # Extract internal fields before saving
            fragment_text = acto.pop("_fragment_content", text[:500])
            acto.pop("_fragment_index", None)
            acto.pop("_resumen_fragmento", None)
            acto.pop("_model_used", None)
            
            await create_analisis(
                db,
                boletin_id=boletin_id,
                fragmento=fragment_text,
                analisis_data=acto,
            )
            total_saved += 1
        except Exception as e:
            logger.error(f"Failed to save acto for {filename}: {e}")
    
    await db.commit()
    logger.info(f"Analysis complete for {filename}: {total_saved} actos saved")
    return total_saved
