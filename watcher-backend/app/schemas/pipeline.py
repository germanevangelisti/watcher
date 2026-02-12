"""
Pipeline Schemas - Models for document processing pipeline

The pipeline processes documents through these stages:
1. uploaded -> 2. extracting -> 3. extracted -> 4. cleaning -> 5. cleaned 
-> 6. chunking -> 7. chunked -> 8. enriching -> 9. enriched 
-> 10. indexing -> 11. indexed (or failed)
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class PipelineStage(str, Enum):
    """Pipeline processing stages."""
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    CLEANING = "cleaning"
    CLEANED = "cleaned"
    CHUNKING = "chunking"
    CHUNKED = "chunked"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


# =============================================================================
# NEW: Configurable PipelineConfig schemas (per-stage configuration)
# =============================================================================

class ExtractionConfig(BaseModel):
    """Opciones de extraccion de texto desde PDF."""
    extractor: str = Field("pdfplumber", description="Extractor: 'pdfplumber' | 'pypdf2'")


class CleaningConfig(BaseModel):
    """Opciones de limpieza de texto."""
    enabled: bool = Field(True, description="Habilitar limpieza de texto")
    fix_encoding: bool = Field(True, description="Corregir encoding con ftfy")
    normalize_unicode: bool = Field(True, description="Normalizacion NFKC")
    normalize_whitespace: bool = Field(True, description="Limpieza de whitespace")
    remove_artifacts: bool = Field(True, description="Remover artefactos de PDF")
    normalize_legal_text: bool = Field(True, description="Normalizar texto legal")


class ChunkingConfigSchema(BaseModel):
    """Opciones de chunking."""
    chunk_size: int = Field(1000, ge=100, le=5000, description="Tamano de chunk en caracteres")
    chunk_overlap: int = Field(200, ge=0, le=1000, description="Overlap entre chunks")
    min_chunk_size: int = Field(100, ge=50, le=500, description="Tamano minimo de chunk")
    strategy: str = Field("recursive", description="Estrategia de chunking")


class EnrichmentConfig(BaseModel):
    """Opciones de enriquecimiento de metadata."""
    enabled: bool = Field(True, description="Habilitar enriquecimiento")
    detect_section_type: bool = Field(True, description="Detectar tipo de seccion")
    detect_amounts: bool = Field(True, description="Detectar montos")
    detect_tables: bool = Field(True, description="Detectar tablas")
    extract_entities: bool = Field(True, description="Extraer entidades")


class IndexingConfig(BaseModel):
    """Opciones de indexacion."""
    use_sqlite: bool = Field(True, description="Guardar ChunkRecord en SQLite")
    use_fts5: bool = Field(True, description="Full-text search index")
    use_chromadb: bool = Field(True, description="Vector embeddings en ChromaDB")
    embedding_model: str = Field("gemini-embedding-001", description="Modelo de embeddings")


class PipelineConfig(BaseModel):
    """Configuracion completa del pipeline."""
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    cleaning: CleaningConfig = Field(default_factory=CleaningConfig)
    chunking: ChunkingConfigSchema = Field(default_factory=ChunkingConfigSchema)
    enrichment: EnrichmentConfig = Field(default_factory=EnrichmentConfig)
    indexing: IndexingConfig = Field(default_factory=IndexingConfig)


# =============================================================================
# Legacy schemas (kept for backward compatibility)
# =============================================================================

class PipelineOptions(BaseModel):
    """Configuration options for pipeline processing (legacy)."""
    chunk_size: int = Field(1000, ge=100, le=5000, description="Chunk size in characters")
    chunk_overlap: int = Field(200, ge=0, le=1000, description="Overlap between chunks")
    skip_cleaning: bool = Field(False, description="Skip text cleaning stage")
    skip_enrichment: bool = Field(False, description="Skip metadata enrichment")
    use_triple_indexing: bool = Field(True, description="Use atomic triple indexing")


class StageStats(BaseModel):
    """Statistics for a single pipeline stage."""
    stage: PipelineStage
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PipelineStatus(BaseModel):
    """Current status of a pipeline execution."""
    file_id: int
    document_id: str
    current_stage: PipelineStage
    progress_pct: float = Field(0.0, ge=0.0, le=100.0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    stage_history: List[StageStats] = Field(default_factory=list)


class PipelineRequest(BaseModel):
    """Request to process a document through the pipeline."""
    options: Optional[PipelineOptions] = None


class PipelineResponse(BaseModel):
    """Response from pipeline processing."""
    file_id: int
    document_id: str
    success: bool
    current_stage: PipelineStage
    total_duration_ms: float
    stages: List[StageStats]
    error: Optional[str] = None
    chunks_created: Optional[int] = None
    chunks_indexed: Optional[int] = None


class BatchPipelineRequest(BaseModel):
    """Request to process multiple documents."""
    file_ids: List[int] = Field(..., min_length=1, max_length=100)
    options: Optional[PipelineOptions] = None


class BatchPipelineResponse(BaseModel):
    """Response from batch pipeline processing."""
    total_files: int
    successful: int
    failed: int
    results: List[PipelineResponse]


class PipelineStatsResponse(BaseModel):
    """Statistics about pipeline usage."""
    total_processed: int
    total_successful: int
    total_failed: int
    average_duration_ms: float
    by_stage: Dict[str, int]
    recent_executions: List[PipelineStatus]
