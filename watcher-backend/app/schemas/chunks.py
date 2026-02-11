"""
Schemas para ChunkRecord - Epic 3: Feature Engineering

Pydantic models para validación y serialización de chunks.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ChunkRecordBase(BaseModel):
    """Base schema para ChunkRecord."""
    document_id: str = Field(description="ID único del documento")
    boletin_id: Optional[int] = Field(None, description="ID del boletín (si aplica)")
    chunk_index: int = Field(description="Índice del chunk (0-based)")
    text: str = Field(description="Texto del chunk")
    num_chars: int = Field(description="Número de caracteres")
    start_char: Optional[int] = Field(None, description="Posición inicial")
    end_char: Optional[int] = Field(None, description="Posición final")
    
    # Metadata enriquecida
    section_type: Optional[str] = Field(None, description="Tipo de sección")
    topic: Optional[str] = Field(None, description="Tema principal")
    language: str = Field(default="es", description="Idioma")
    has_tables: bool = Field(default=False, description="Contiene tablas")
    has_amounts: bool = Field(default=False, description="Contiene montos")
    entities_json: Optional[Dict[str, Any]] = Field(None, description="Entidades detectadas")
    
    # Embedding info
    embedding_model: Optional[str] = Field(None, description="Modelo de embedding usado")
    embedding_dimensions: Optional[int] = Field(None, description="Dimensiones del embedding")


class ChunkRecordCreate(ChunkRecordBase):
    """Schema para crear ChunkRecord."""
    pass


class ChunkRecordUpdate(BaseModel):
    """Schema para actualizar ChunkRecord."""
    text: Optional[str] = None
    section_type: Optional[str] = None
    topic: Optional[str] = None
    has_tables: Optional[bool] = None
    has_amounts: Optional[bool] = None
    entities_json: Optional[Dict[str, Any]] = None
    embedding_model: Optional[str] = None
    embedding_dimensions: Optional[int] = None
    indexed_at: Optional[datetime] = None


class ChunkRecordResponse(ChunkRecordBase):
    """Schema para respuestas de ChunkRecord."""
    id: int
    chunk_hash: Optional[str]
    indexed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ChunkRecordList(BaseModel):
    """Schema para lista de ChunkRecords."""
    chunks: List[ChunkRecordResponse]
    total: int
    document_id: str
    
    class Config:
        from_attributes = True


class ChunkRecordStats(BaseModel):
    """Estadísticas de chunks."""
    total_chunks: int
    total_chars: int
    avg_chunk_size: float
    sections_by_type: Dict[str, int]
    chunks_with_amounts: int
    chunks_with_tables: int
    indexed_chunks: int
