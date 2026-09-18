"""
Base Adapter - Abstract interface for data adapters

Adapters normalize data from different scrapers into a common schema
that can be consumed by the AI agents and persistence layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    """Types of data sources"""
    PROVINCIAL = "provincial"
    MUNICIPAL = "municipal"
    NATIONAL = "national"


class DocumentCategory(str, Enum):
    """Categories of documents"""
    BOLETIN = "boletin"
    PRESUPUESTO = "presupuesto"
    CONTRATO = "contrato"
    OBRA = "obra"
    DECRETO = "decreto"
    RESOLUCION = "resolucion"
    COMPRA = "compra"
    MENCION = "mencion"


@dataclass
class DocumentSchema:
    """
    Unified schema for documents from any source.
    
    This schema normalizes data from different portals into a common format.
    """
    # Core identification
    source_type: SourceType
    document_id: str
    filename: str
    category: DocumentCategory

    # Dates
    document_date: date
    ingestion_date: datetime = field(default_factory=datetime.now)

    # Content
    title: str | None = None
    content: str | None = None
    summary: str | None = None

    # Location/Jurisdiction
    jurisdiction_id: int | None = None
    jurisdiction_name: str | None = None

    # Classification
    section: str | None = None
    subsection: str | None = None
    tags: list[str] = field(default_factory=list)

    # Storage
    file_path: str | None = None
    file_size: int | None = None

    # Extracted entities
    entities: dict[str, Any] = field(default_factory=dict)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Processing status
    extraction_status: str = "pending"  # pending, extracted, failed
    analysis_status: str = "pending"  # pending, analyzed, failed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "source_type": self.source_type.value,
            "document_id": self.document_id,
            "filename": self.filename,
            "category": self.category.value,
            "document_date": self.document_date.isoformat() if isinstance(self.document_date, date) else self.document_date,
            "ingestion_date": self.ingestion_date.isoformat() if isinstance(self.ingestion_date, datetime) else self.ingestion_date,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "jurisdiction_id": self.jurisdiction_id,
            "jurisdiction_name": self.jurisdiction_name,
            "section": self.section,
            "subsection": self.subsection,
            "tags": self.tags,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "entities": self.entities,
            "metadata": self.metadata,
            "extraction_status": self.extraction_status,
            "analysis_status": self.analysis_status,
        }


@dataclass
class AdapterResult:
    """Result of an adaptation operation"""
    success: bool
    document: DocumentSchema | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


class BaseAdapter(ABC):
    """
    Abstract base class for data adapters.
    
    Each adapter transforms data from a specific source format
    into the unified DocumentSchema.
    """

    def __init__(self, source_type: SourceType):
        """
        Initialize adapter.
        
        Args:
            source_type: Type of data source this adapter handles
        """
        self.source_type = source_type
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0
        }

    @abstractmethod
    async def adapt_document(
        self,
        raw_data: dict[str, Any],
        **kwargs
    ) -> AdapterResult:
        """
        Transform raw scraped data into normalized DocumentSchema.
        
        Args:
            raw_data: Raw data from scraper
            **kwargs: Additional context for adaptation
            
        Returns:
            AdapterResult with normalized document
        """
        pass

    @abstractmethod
    async def adapt_batch(
        self,
        raw_data_list: list[dict[str, Any]],
        **kwargs
    ) -> list[AdapterResult]:
        """
        Transform a batch of raw documents.
        
        Args:
            raw_data_list: List of raw data from scraper
            **kwargs: Additional context for adaptation
            
        Returns:
            List of AdapterResult objects
        """
        pass

    @abstractmethod
    def validate_document(self, document: DocumentSchema) -> bool:
        """
        Validate that a document has all required fields.
        
        Args:
            document: Document to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get adapter statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0
        }

    def _update_stats(self, result: AdapterResult):
        """Update statistics based on result."""
        self.stats["total_processed"] += 1

        if result.success:
            self.stats["successful"] += 1
        else:
            self.stats["failed"] += 1

        if result.warnings:
            self.stats["warnings"] += len(result.warnings)
