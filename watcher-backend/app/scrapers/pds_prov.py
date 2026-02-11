"""
PDS-PROV - Provincial Data Scraper

Specialized scraper for Boletín Oficial de la Provincia de Córdoba.
Downloads official bulletins from the provincial government portal.
"""

import asyncio
import logging
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import httpx

from .base_scraper import (
    BaseScraper,
    ScraperConfig,
    ScraperResult,
    ScraperType,
    DocumentType
)
from app.services.hash_utils import compute_sha256

logger = logging.getLogger(__name__)


# Default User-Agents for simulating different browsers
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]


class ProvincialScraper(BaseScraper):
    """
    Scraper for Boletín Oficial de Córdoba (Provincial level).
    
    Downloads official bulletins from:
    https://boletinoficial.cba.gov.ar/
    """
    
    # URL template for provincial bulletins
    BASE_URL_TEMPLATE = "https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/{year}/{month:02d}/{section}_Secc_{day:02d}{month:02d}{y_short}.pdf"
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize provincial scraper.
        
        Args:
            config: Optional configuration. If not provided, uses defaults.
        """
        if config is None:
            config = ScraperConfig(
                scraper_type=ScraperType.PROVINCIAL,
                base_url="https://boletinoficial.cba.gov.ar",
                output_dir=Path("/Users/germanevangelisti/watcher-agent/boletines"),
                rate_limit_delay=2.5,
                max_retries=3,
                timeout=30.0,
                user_agents=DEFAULT_USER_AGENTS,
                skip_weekends=True,
                sections=[1, 2, 3, 4, 5]
            )
        
        super().__init__(config)
        
        if not self.config.user_agents:
            self.config.user_agents = DEFAULT_USER_AGENTS
    
    def get_file_path(
        self,
        target_date: date,
        document_type: DocumentType,
        section: Optional[int] = None,
        **kwargs
    ) -> Path:
        """
        Get the file path for a provincial bulletin.
        
        Args:
            target_date: Date of the bulletin
            document_type: Type of document (should be BOLETIN)
            section: Section number (1-5)
            
        Returns:
            Path where the file should be stored
        """
        if section is None:
            section = kwargs.get('section', 1)
        
        filename = f"{target_date.year}{target_date.month:02d}{target_date.day:02d}_{section}_Secc.pdf"
        
        # Organize by year/month structure
        return self.config.output_dir / str(target_date.year) / f"{target_date.month:02d}" / filename
    
    def validate_file(self, filepath: Path) -> bool:
        """
        Validate that a downloaded bulletin is valid.
        
        Args:
            filepath: Path to the file
            
        Returns:
            True if file exists and is larger than 10KB
        """
        if not filepath.exists():
            return False
        
        file_size = filepath.stat().st_size
        # Valid PDFs should be at least 10KB
        return file_size > 10240
    
    async def download_single(
        self,
        target_date: date,
        document_type: DocumentType = DocumentType.BOLETIN,
        section: int = 1,
        **kwargs
    ) -> ScraperResult:
        """
        Download a single bulletin for a specific date and section.
        
        Args:
            target_date: Date of the bulletin
            document_type: Type of document (BOLETIN)
            section: Section number (1-5)
            
        Returns:
            ScraperResult with download status
        """
        # Build URL
        y_short = int(str(target_date.year)[2:])
        url = self.BASE_URL_TEMPLATE.format(
            year=target_date.year,
            y_short=y_short,
            month=target_date.month,
            day=target_date.day,
            section=section
        )
        
        # Get filepath
        filepath = self.get_file_path(target_date, document_type, section=section)
        filename = filepath.name
        
        # Create directory if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file already exists and is valid
        if self.validate_file(filepath):
            # Compute hash for existing file (Epic 1.1)
            file_hash = compute_sha256(filepath)
            file_size = filepath.stat().st_size
            
            result = ScraperResult(
                filename=filename,
                status="exists",
                size=file_size,
                path=str(filepath.relative_to(self.config.output_dir)),
                metadata={
                    "date": target_date.isoformat(),
                    "section": section,
                    "file_hash": file_hash,
                    "file_size_bytes": file_size
                }
            )
            self._update_stats(result)
            return result
        
        # If exists but invalid, remove it
        if filepath.exists():
            logger.warning(f"File {filename} exists but is invalid, re-downloading")
            filepath.unlink()
        
        # Download file
        try:
            headers = {
                "User-Agent": random.choice(self.config.user_agents),
                "Accept": "application/pdf",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            }
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('application/pdf'):
                    filepath.write_bytes(response.content)
                    
                    # Compute SHA256 hash for deduplication (Epic 1.1)
                    file_hash = compute_sha256(filepath)
                    
                    logger.info(f"✅ Downloaded: {filename} (SHA256: {file_hash[:16]}...)")
                    
                    result = ScraperResult(
                        filename=filename,
                        status="downloaded",
                        size=len(response.content),
                        path=str(filepath.relative_to(self.config.output_dir)),
                        url=url,
                        metadata={
                            "date": target_date.isoformat(),
                            "section": section,
                            "file_hash": file_hash,
                            "file_size_bytes": len(response.content)
                        }
                    )
                else:
                    logger.warning(f"❌ Not available: {filename} (status {response.status_code})")
                    result = ScraperResult(
                        filename=filename,
                        status="not_available",
                        error=f"HTTP {response.status_code}",
                        url=url,
                        metadata={
                            "date": target_date.isoformat(),
                            "section": section
                        }
                    )
        
        except Exception as e:
            logger.error(f"⚠️ Error downloading {filename}: {e}")
            result = ScraperResult(
                filename=filename,
                status="error",
                error=str(e),
                url=url,
                metadata={
                    "date": target_date.isoformat(),
                    "section": section
                }
            )
        
        self._update_stats(result)
        return result
    
    async def download_range(
        self,
        start_date: date,
        end_date: date,
        document_type: DocumentType = DocumentType.BOLETIN,
        sections: Optional[List[int]] = None,
        **kwargs
    ) -> List[ScraperResult]:
        """
        Download bulletins for a date range.
        
        Args:
            start_date: Start date
            end_date: End date (inclusive)
            document_type: Type of document
            sections: List of sections to download (default: [1,2,3,4,5])
            
        Returns:
            List of ScraperResult objects
        """
        if sections is None:
            sections = self.config.sections or [1, 2, 3, 4, 5]
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends if configured
            if self.config.skip_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Download all sections for this date
            for section in sections:
                # Rate limiting with human-like delays
                if len(results) > 0 and len(results) % 10 == 0:
                    # Longer pause every 10 files
                    await asyncio.sleep(random.uniform(5.0, 8.0))
                else:
                    # Normal pause
                    await asyncio.sleep(random.uniform(
                        self.config.rate_limit_delay,
                        self.config.rate_limit_delay + 2.0
                    ))
                
                result = await self.download_single(
                    target_date=current_date,
                    document_type=document_type,
                    section=section
                )
                results.append(result)
            
            current_date += timedelta(days=1)
        
        return results
    
    def get_available_sections(self) -> List[int]:
        """
        Get list of available sections for provincial bulletins.
        
        Returns:
            List of section numbers
        """
        return [1, 2, 3, 4, 5]


# Convenience function to create a provincial scraper
def create_provincial_scraper(
    output_dir: Optional[Path] = None,
    **kwargs
) -> ProvincialScraper:
    """
    Create a provincial scraper with custom configuration.
    
    Args:
        output_dir: Optional output directory
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured ProvincialScraper instance
    """
    config_dict = {
        "scraper_type": ScraperType.PROVINCIAL,
        "base_url": "https://boletinoficial.cba.gov.ar",
        "output_dir": output_dir or Path("/Users/germanevangelisti/watcher-agent/boletines"),
    }
    config_dict.update(kwargs)
    
    config = ScraperConfig(**config_dict)
    return ProvincialScraper(config)
