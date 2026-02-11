"""
Base Scraper - Abstract interface for all data scrapers

This module defines the contract that all scrapers must implement,
enabling a pluggable architecture for multiple data sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum


class ScraperType(str, Enum):
    """Types of scrapers available"""
    PROVINCIAL = "provincial"
    MUNICIPAL = "municipal"
    NATIONAL = "national"


class DocumentType(str, Enum):
    """Types of documents that can be scraped"""
    BOLETIN = "boletin"
    PRESUPUESTO = "presupuesto"
    CONTRATO = "contrato"
    OBRA = "obra"
    DECRETO = "decreto"
    RESOLUCION = "resolucion"
    COMPRA = "compra"


@dataclass
class ScraperConfig:
    """Configuration for a scraper"""
    scraper_type: ScraperType
    base_url: str
    output_dir: Path
    rate_limit_delay: float = 2.0
    max_retries: int = 3
    timeout: float = 30.0
    user_agents: Optional[List[str]] = None
    skip_weekends: bool = True
    sections: Optional[List[int]] = None


@dataclass
class ScraperResult:
    """Result of a scraping operation"""
    filename: str
    status: str  # 'downloaded', 'exists', 'not_available', 'error'
    size: Optional[int] = None
    path: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Each scraper must implement the core methods for downloading,
    validating, and organizing data from a specific source.
    """
    
    def __init__(self, config: ScraperConfig):
        """
        Initialize the scraper with configuration.
        
        Args:
            config: ScraperConfig with scraper settings
        """
        self.config = config
        self.stats = {
            "total_requested": 0,
            "downloaded": 0,
            "already_existed": 0,
            "failed": 0,
            "errors": []
        }
    
    @abstractmethod
    async def download_single(
        self,
        target_date: date,
        document_type: DocumentType,
        **kwargs
    ) -> ScraperResult:
        """
        Download a single document for a specific date.
        
        Args:
            target_date: Date of the document
            document_type: Type of document to download
            **kwargs: Additional parameters specific to the scraper
            
        Returns:
            ScraperResult with download status
        """
        pass
    
    @abstractmethod
    async def download_range(
        self,
        start_date: date,
        end_date: date,
        document_type: DocumentType,
        **kwargs
    ) -> List[ScraperResult]:
        """
        Download documents for a date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range (inclusive)
            document_type: Type of documents to download
            **kwargs: Additional parameters specific to the scraper
            
        Returns:
            List of ScraperResult objects
        """
        pass
    
    @abstractmethod
    def validate_file(self, filepath: Path) -> bool:
        """
        Validate that a downloaded file is valid.
        
        Args:
            filepath: Path to file to validate
            
        Returns:
            True if file is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_path(
        self,
        target_date: date,
        document_type: DocumentType,
        **kwargs
    ) -> Path:
        """
        Get the expected file path for a document.
        
        Args:
            target_date: Date of the document
            document_type: Type of document
            **kwargs: Additional parameters for path generation
            
        Returns:
            Path where the file should be stored
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get scraping statistics.
        
        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            "total_requested": 0,
            "downloaded": 0,
            "already_existed": 0,
            "failed": 0,
            "errors": []
        }
    
    def _update_stats(self, result: ScraperResult):
        """Update statistics based on a scraping result."""
        self.stats["total_requested"] += 1
        
        if result.status == "downloaded":
            self.stats["downloaded"] += 1
        elif result.status == "exists":
            self.stats["already_existed"] += 1
        elif result.status in ["error", "not_available"]:
            self.stats["failed"] += 1
            if result.error:
                self.stats["errors"].append(f"{result.filename}: {result.error}")
