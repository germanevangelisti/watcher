"""
Pipeline endpoints - Unified document processing pipeline

Provides endpoints for:
- Processing single documents through the complete pipeline
- Batch processing multiple documents
- Checking pipeline status
- Getting pipeline statistics
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.services.pipeline_service import get_pipeline_service
from app.schemas.pipeline import (
    PipelineRequest,
    PipelineResponse,
    PipelineOptions,
    BatchPipelineRequest,
    BatchPipelineResponse,
    PipelineStatsResponse,
    PipelineStatus
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process/{file_id}", response_model=PipelineResponse)
async def process_document(
    file_id: int,
    request: PipelineRequest = None,
    db: Session = Depends(get_db)
):
    """
    Process a single document through the complete pipeline.
    
    Pipeline stages:
    1. Extract text from file
    2. Clean text (optional)
    3. Chunk text
    4. Enrich chunks with metadata
    5. Triple-index (ChromaDB + SQLite + FTS5)
    
    Args:
        file_id: ID of the file to process
        request: Optional processing options
        db: Database session
    
    Returns:
        PipelineResponse with results and timing for each stage
    """
    try:
        pipeline_service = get_pipeline_service(db)
        
        options = request.options if request else None
        
        result = await pipeline_service.process_document(file_id, options)
        
        return result
    
    except Exception as e:
        logger.error(f"Error in pipeline endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchPipelineResponse)
async def process_batch(
    request: BatchPipelineRequest,
    db: Session = Depends(get_db)
):
    """
    Process multiple documents through the pipeline.
    
    Processes documents sequentially (not in parallel to avoid resource contention).
    
    Args:
        request: Batch request with file IDs and options
        db: Database session
    
    Returns:
        BatchPipelineResponse with individual results for each file
    """
    try:
        pipeline_service = get_pipeline_service(db)
        
        results = await pipeline_service.process_batch(
            request.file_ids,
            request.options
        )
        
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        return BatchPipelineResponse(
            total_files=len(results),
            successful=successful,
            failed=failed,
            results=results
        )
    
    except Exception as e:
        logger.error(f"Error in batch pipeline endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{file_id}", response_model=PipelineStatus)
async def get_pipeline_status(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the current pipeline processing status for a file.
    
    This endpoint is useful for polling during long-running operations.
    
    Args:
        file_id: ID of the file
        db: Database session
    
    Returns:
        PipelineStatus with current stage and progress
    """
    try:
        # TODO: Implement actual status tracking
        # This would query a pipeline_executions table or similar
        
        raise HTTPException(
            status_code=501,
            detail="Status tracking not yet implemented. Process documents and check the response for completion status."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats(db: Session = Depends(get_db)):
    """
    Get statistics about pipeline usage.
    
    Returns aggregate statistics about pipeline executions,
    success/failure rates, and average processing times.
    
    Args:
        db: Database session
    
    Returns:
        PipelineStatsResponse with statistics
    """
    try:
        # TODO: Implement actual statistics tracking
        # This would aggregate data from pipeline_executions table
        
        return PipelineStatsResponse(
            total_processed=0,
            total_successful=0,
            total_failed=0,
            average_duration_ms=0.0,
            by_stage={},
            recent_executions=[]
        )
    
    except Exception as e:
        logger.error(f"Error getting pipeline stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-pipeline", response_model=PipelineResponse)
async def test_pipeline(db: Session = Depends(get_db)):
    """
    Test endpoint for pipeline functionality.
    
    Creates a dummy file and processes it through the pipeline
    to verify everything is working correctly.
    
    Args:
        db: Database session
    
    Returns:
        PipelineResponse from test execution
    """
    try:
        import tempfile
        from pathlib import Path
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""
            DECRETO 123/2024
            
            El Ministerio de Salud establece nuevas normas para la atención sanitaria.
            
            ARTÍCULO 1: Se aprueba el protocolo de atención primaria.
            ARTÍCULO 2: Los hospitales públicos deberán implementar estas normas en 60 días.
            
            RESOLUCIÓN ADMINISTRATIVA
            
            Se autoriza la contratación directa de personal médico especializado.
            El presupuesto asignado es de $5.000.000 para el año fiscal 2024.
            """)
            test_file_path = f.name
        
        try:
            # Mock a file_id
            # In production, this would be a real database entry
            test_file_id = 999999
            
            # Override the _get_file_path method temporarily
            pipeline_service = get_pipeline_service(db)
            
            # Monkey-patch for testing
            async def mock_get_file_path(file_id: int):
                return test_file_path
            
            pipeline_service._get_file_path = mock_get_file_path
            
            # Process
            result = await pipeline_service.process_document(
                test_file_id,
                PipelineOptions()
            )
            
            return result
        
        finally:
            # Clean up
            try:
                Path(test_file_path).unlink()
            except Exception:
                pass
    
    except Exception as e:
        logger.error(f"Error in pipeline test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
