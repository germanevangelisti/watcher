"""
Schemas para ChunkRecord - Epic 3: Feature Engineering

Pydantic models para validación y serialización de chunks.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChunkRecordBase(BaseModel):
    """Base schema para ChunkRecord."""
    document_id: str = Field(description="ID único del documento")
    boletin_id: int | None = Field(None, description="ID del boletín (si aplica)")
    chunk_index: int = Field(description="Índice del chunk (0-based)")
    text: str = Field(description="Texto del chunk")
    num_chars: int = Field(description="Número de caracteres")
    start_char: int | None = Field(None, description="Posición inicial")
    end_char: int | None = Field(None, description="Posición final")

    # Metadata enriquecida
    section_type: str | None = Field(None, description="Tipo de sección")
    topic: str | None = Field(None, description="Tema principal")
    language: str = Field(default="es", description="Idioma")
    has_tables: bool = Field(default=False, description="Contiene tablas")
    has_amounts: bool = Field(default=False, description="Contiene montos")
    entities_json: dict[str, Any] | None = Field(None, description="Entidades detectadas")

    # Embedding info
    embedding_model: str | None = Field(None, description="Modelo de embedding usado")
    embedding_dimensions: int | None = Field(None, description="Dimensiones del embedding")


class ChunkRecordCreate(ChunkRecordBase):
    """Schema para crear ChunkRecord."""
    pass


class ChunkRecordUpdate(BaseModel):
    """Schema para actualizar ChunkRecord."""
    text: str | None = None
    section_type: str | None = None
    topic: str | None = None
    has_tables: bool | None = None
    has_amounts: bool | None = None
    entities_json: dict[str, Any] | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    indexed_at: datetime | None = None


class ChunkRecordResponse(ChunkRecordBase):
    """Schema para respuestas de ChunkRecord."""
    id: int
    chunk_hash: str | None
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ChunkRecordList(BaseModel):
    """Schema para lista de ChunkRecords."""
    chunks: list[ChunkRecordResponse]
    total: int
    document_id: str

    class Config:
        from_attributes = True


class ChunkRecordStats(BaseModel):
    """Estadísticas de chunks."""
    total_chunks: int
    total_chars: int
    avg_chunk_size: float
    sections_by_type: dict[str, int]
    chunks_with_amounts: int
    chunks_with_tables: int
    indexed_chunks: int
