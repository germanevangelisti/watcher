"""
Pipeline Service - Orchestrates end-to-end document processing pipeline

Pipeline stages:
1. Extract text from uploaded file
2. Clean text (optional)
3. Chunk text
4. Enrich chunks with metadata
5. Triple-index chunks (ChromaDB + SQLite + FTS5)

Each stage is tracked with timing and error handling.

MIGRATED to AsyncSession (P-1).
"""

import logging
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Import services
try:
    from .text_cleaner import TextCleaner
    TEXT_CLEANER_AVAILABLE = True
except ImportError:
    logger.warning("TextCleaner not available")
    TEXT_CLEANER_AVAILABLE = False

try:
    from .chunking_service import ChunkingService, ChunkingConfig
    CHUNKING_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("ChunkingService not available")
    CHUNKING_SERVICE_AVAILABLE = False

try:
    from .indexing_service import get_indexing_service
    INDEXING_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("IndexingService not available")
    INDEXING_SERVICE_AVAILABLE = False

# Import schemas
from ..schemas.pipeline import (
    PipelineStage, PipelineOptions, StageStats, PipelineStatus, PipelineResponse
)

# Import extractors
try:
    from .extractors import ExtractorRegistry
    EXTRACTOR_AVAILABLE = True
except ImportError:
    logger.warning("ExtractorRegistry not available")
    EXTRACTOR_AVAILABLE = False

# Import models
try:
    from ..db.models import Boletin
    BOLETIN_MODEL_AVAILABLE = True
except ImportError:
    logger.warning("Boletin model not available")
    BOLETIN_MODEL_AVAILABLE = False


class PipelineService:
    """
    Service for orchestrating the complete document processing pipeline.
    
    Handles extraction, cleaning, chunking, enrichment, and indexing.
    Uses AsyncSession for database operations.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize pipeline service.
        
        Args:
            db_session: SQLAlchemy AsyncSession
        """
        self.db = db_session
        
        # Initialize services
        self.text_cleaner = None
        if TEXT_CLEANER_AVAILABLE:
            self.text_cleaner = TextCleaner()
        
        self.chunking_service = None
        if CHUNKING_SERVICE_AVAILABLE:
            self.chunking_service = ChunkingService()
        
        self.indexing_service = None
        if INDEXING_SERVICE_AVAILABLE:
            self.indexing_service = get_indexing_service(db_session)
    
    async def process_document(
        self,
        file_id: int,
        options: Optional[PipelineOptions] = None
    ) -> PipelineResponse:
        """
        Process a document through the complete pipeline.
        
        Args:
            file_id: ID of the file/document to process
            options: Optional configuration for pipeline stages
        
        Returns:
            PipelineResponse with results and timing
        """
        if options is None:
            options = PipelineOptions()
        
        # Initialize tracking
        document_id = f"file_{file_id}"
        started_at = datetime.utcnow()
        stages: List[StageStats] = []
        current_stage = PipelineStage.UPLOADED
        
        # Extracted data
        extracted_text = None
        cleaned_text = None
        chunks = None
        
        try:
            # ============================================
            # Stage 1: Find and validate file
            # ============================================
            stage_start = datetime.utcnow()
            current_stage = PipelineStage.EXTRACTING
            
            file_path = await self._get_file_path(file_id)
            if not file_path or not Path(file_path).exists():
                raise FileNotFoundError(f"File {file_id} not found at {file_path}")
            
            stages.append(StageStats(
                stage=PipelineStage.UPLOADED,
                started_at=stage_start,
                completed_at=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - stage_start).total_seconds() * 1000,
                success=True,
                details={"file_id": file_id, "file_path": str(file_path)}
            ))
            
            # ============================================
            # Stage 2: Extract text
            # ============================================
            stage_start = datetime.utcnow()
            current_stage = PipelineStage.EXTRACTING
            
            if not EXTRACTOR_AVAILABLE:
                raise Exception("ExtractorRegistry not available")
            
            extraction_result = await ExtractorRegistry.extract(Path(file_path))
            
            if not extraction_result.success:
                raise Exception(f"Extraction failed: {extraction_result.error}")
            
            extracted_text = extraction_result.full_text
            
            stages.append(StageStats(
                stage=PipelineStage.EXTRACTING,
                started_at=stage_start,
                completed_at=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - stage_start).total_seconds() * 1000,
                success=True,
                details={
                    "pages": len(extraction_result.pages),
                    "total_chars": len(extracted_text),
                }
            ))
            
            current_stage = PipelineStage.EXTRACTED
            
            # ============================================
            # Stage 3: Clean text (optional)
            # ============================================
            if not options.skip_cleaning and self.text_cleaner:
                stage_start = datetime.utcnow()
                current_stage = PipelineStage.CLEANING
                
                cleaned_text = self.text_cleaner.clean(extracted_text)
                
                stages.append(StageStats(
                    stage=PipelineStage.CLEANING,
                    started_at=stage_start,
                    completed_at=datetime.utcnow(),
                    duration_ms=(datetime.utcnow() - stage_start).total_seconds() * 1000,
                    success=True,
                    details={
                        "chars_before": len(extracted_text),
                        "chars_after": len(cleaned_text)
                    }
                ))
                
                current_stage = PipelineStage.CLEANED
            else:
                cleaned_text = extracted_text
                if options.skip_cleaning:
                    logger.info("Skipping text cleaning (per options)")
            
            # ============================================
            # Stage 4: Chunk text
            # ============================================
            stage_start = datetime.utcnow()
            current_stage = PipelineStage.CHUNKING
            
            if not self.chunking_service:
                raise Exception("ChunkingService not available")
            
            config = ChunkingConfig(
                chunk_size=options.chunk_size,
                chunk_overlap=options.chunk_overlap
            )
            
            chunks = self.chunking_service.chunk(cleaned_text, config)
            
            stages.append(StageStats(
                stage=PipelineStage.CHUNKING,
                started_at=stage_start,
                completed_at=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - stage_start).total_seconds() * 1000,
                success=True,
                details={
                    "total_chunks": len(chunks),
                    "chunk_size": options.chunk_size,
                    "chunk_overlap": options.chunk_overlap
                }
            ))
            
            current_stage = PipelineStage.CHUNKED
            
            # ============================================
            # Stage 5: Enrich metadata (handled in indexing)
            # ============================================
            if not options.skip_enrichment:
                stage_start = datetime.utcnow()
                current_stage = PipelineStage.ENRICHING
                
                stages.append(StageStats(
                    stage=PipelineStage.ENRICHING,
                    started_at=stage_start,
                    completed_at=datetime.utcnow(),
                    duration_ms=(datetime.utcnow() - stage_start).total_seconds() * 1000,
                    success=True,
                    details={"chunks_to_enrich": len(chunks)}
                ))
                
                current_stage = PipelineStage.ENRICHED
            
            # ============================================
            # Stage 6: Triple-index chunks
            # ============================================
            stage_start = datetime.utcnow()
            current_stage = PipelineStage.INDEXING
            
            if not self.indexing_service:
                raise Exception("IndexingService not available")
            
            metadata = {
                "file_id": file_id,
                "source": "pipeline"
            }
            
            indexing_result = await self.indexing_service.index_document(
                document_id=document_id,
                chunks=chunks,
                metadata=metadata
            )
            
            if not indexing_result.success:
                raise Exception(f"Indexing failed: {indexing_result.error}")
            
            stages.append(StageStats(
                stage=PipelineStage.INDEXING,
                started_at=stage_start,
                completed_at=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - stage_start).total_seconds() * 1000,
                success=True,
                details={
                    "chunks_indexed": indexing_result.chunks_indexed,
                    "triple_indexed": True
                }
            ))
            
            current_stage = PipelineStage.INDEXED
            
            # ============================================
            # Success!
            # ============================================
            completed_at = datetime.utcnow()
            total_duration = (completed_at - started_at).total_seconds() * 1000
            
            logger.info(f"Pipeline completed for file {file_id} in {total_duration:.2f}ms")
            
            return PipelineResponse(
                file_id=file_id,
                document_id=document_id,
                success=True,
                current_stage=current_stage,
                total_duration_ms=total_duration,
                stages=stages,
                chunks_created=len(chunks) if chunks else 0,
                chunks_indexed=indexing_result.chunks_indexed
            )
        
        except Exception as e:
            logger.error(f"Pipeline failed at stage {current_stage}: {e}", exc_info=True)
            
            stages.append(StageStats(
                stage=current_stage,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_ms=0,
                success=False,
                error=str(e)
            ))
            
            completed_at = datetime.utcnow()
            total_duration = (completed_at - started_at).total_seconds() * 1000
            
            return PipelineResponse(
                file_id=file_id,
                document_id=document_id,
                success=False,
                current_stage=PipelineStage.FAILED,
                total_duration_ms=total_duration,
                stages=stages,
                error=str(e)
            )
    
    async def _get_file_path(self, file_id: int) -> Optional[str]:
        """
        Get the file path for a file ID by querying the database.
        
        Args:
            file_id: Boletin ID
        
        Returns:
            File path or None
        """
        if not BOLETIN_MODEL_AVAILABLE:
            logger.warning("Boletin model not available, cannot resolve file path")
            return None
        
        from ..core.config import settings
        
        result = await self.db.execute(
            select(Boletin).where(Boletin.id == file_id)
        )
        boletin = result.scalar_one_or_none()
        
        if not boletin:
            return None
        
        # Check for .txt first, then PDF in all known directories
        txt_path = settings.DATA_DIR / "processed" / boletin.filename.replace(".pdf", ".txt")
        if txt_path.exists():
            return str(txt_path)
        
        for subdir in ["raw", "uploaded_documents", "pdfs"]:
            pdf_path = settings.DATA_DIR / subdir / boletin.filename
            if pdf_path.exists():
                return str(pdf_path)
        
        return None
    
    async def process_batch(
        self,
        file_ids: List[int],
        options: Optional[PipelineOptions] = None
    ) -> List[PipelineResponse]:
        """
        Process multiple files through the pipeline.
        
        Args:
            file_ids: List of file IDs to process
            options: Optional configuration
        
        Returns:
            List of PipelineResponse objects
        """
        results = []
        
        for file_id in file_ids:
            try:
                result = await self.process_document(file_id, options)
                results.append(result)
                
                if result.success:
                    logger.info(f"Batch: file {file_id} succeeded")
                else:
                    logger.warning(f"Batch: file {file_id} failed: {result.error}")
            
            except Exception as e:
                logger.error(f"Batch processing error for file {file_id}: {e}")
                results.append(PipelineResponse(
                    file_id=file_id,
                    document_id=f"file_{file_id}",
                    success=False,
                    current_stage=PipelineStage.FAILED,
                    total_duration_ms=0,
                    stages=[],
                    error=str(e)
                ))
        
        return results


def get_pipeline_service(db_session: AsyncSession) -> PipelineService:
    """
    Get PipelineService instance.
    
    Args:
        db_session: SQLAlchemy AsyncSession
    
    Returns:
        PipelineService instance
    """
    return PipelineService(db_session)
