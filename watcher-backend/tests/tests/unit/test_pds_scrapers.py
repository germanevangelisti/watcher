"""
Unit tests for PDS (Portal Data Scrapers) layer.

Tests the scraper interfaces and provincial scraper implementation.
"""

import pytest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.scrapers.base_scraper import (
    BaseScraper,
    ScraperConfig,
    ScraperResult,
    ScraperType,
    DocumentType
)
from app.scrapers.pds_prov import ProvincialScraper, create_provincial_scraper


# ============================================================================
# Base Scraper Tests
# ============================================================================

@pytest.mark.pds
def test_base_scraper_interface():
    """Test that BaseScraper is a proper abstract interface."""
    # Should not be able to instantiate directly
    with pytest.raises(TypeError):
        BaseScraper(ScraperConfig(
            scraper_type=ScraperType.PROVINCIAL,
            base_url="test",
            output_dir=Path("/tmp")
        ))


@pytest.mark.pds
def test_scraper_result_creation():
    """Test ScraperResult creation."""
    result = ScraperResult(
        filename="test.pdf",
        status="downloaded",
        size=1024,
        path="2026/01/test.pdf",
        url="https://test.com/test.pdf",
        metadata={"test": True}
    )
    
    assert result.filename == "test.pdf"
    assert result.status == "downloaded"
    assert result.size == 1024
    assert result.metadata["test"] is True


# ============================================================================
# Provincial Scraper Tests
# ============================================================================

@pytest.mark.pds
def test_provincial_scraper_init(sample_scraper_config):
    """Test ProvincialScraper initialization."""
    scraper = ProvincialScraper(sample_scraper_config)
    
    assert scraper.config == sample_scraper_config
    assert scraper.config.scraper_type == ScraperType.PROVINCIAL
    assert scraper.stats["total_requested"] == 0
    assert scraper.stats["downloaded"] == 0


@pytest.mark.pds
def test_provincial_scraper_init_default():
    """Test ProvincialScraper with default config."""
    scraper = ProvincialScraper()
    
    assert scraper.config is not None
    assert scraper.config.scraper_type == ScraperType.PROVINCIAL
    assert scraper.config.sections == [1, 2, 3, 4, 5]


@pytest.mark.pds
def test_provincial_scraper_get_file_path():
    """Test file path generation."""
    scraper = create_provincial_scraper(output_dir=Path("/test"))
    
    target_date = date(2026, 1, 15)
    filepath = scraper.get_file_path(
        target_date=target_date,
        document_type=DocumentType.BOLETIN,
        section=1
    )
    
    assert filepath == Path("/test/2026/01/20260115_1_Secc.pdf")
    assert filepath.parent == Path("/test/2026/01")


@pytest.mark.pds
def test_provincial_scraper_validate_file_valid(temp_output_dir):
    """Test file validation with valid file."""
    scraper = create_provincial_scraper()
    
    # Create a valid file (>10KB)
    test_file = temp_output_dir / "test.pdf"
    test_file.write_bytes(b"x" * 20000)  # 20KB
    
    assert scraper.validate_file(test_file) is True


@pytest.mark.pds
def test_provincial_scraper_validate_file_invalid(temp_output_dir):
    """Test file validation with invalid file."""
    scraper = create_provincial_scraper()
    
    # Create an invalid file (<10KB)
    test_file = temp_output_dir / "test.pdf"
    test_file.write_bytes(b"x" * 5000)  # 5KB
    
    assert scraper.validate_file(test_file) is False


@pytest.mark.pds
def test_provincial_scraper_validate_file_nonexistent():
    """Test file validation with non-existent file."""
    scraper = create_provincial_scraper()
    
    test_file = Path("/nonexistent/file.pdf")
    
    assert scraper.validate_file(test_file) is False


@pytest.mark.pds
@pytest.mark.asyncio
async def test_provincial_scraper_download_single(temp_output_dir, mock_http_client):
    """Test single bulletin download with mock HTTP client."""
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    
    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await scraper.download_single(
            target_date=date(2026, 1, 15),
            document_type=DocumentType.BOLETIN,
            section=1
        )
    
    assert result.filename == "20260115_1_Secc.pdf"
    assert result.status == "downloaded"
    assert result.size > 0
    assert "2026/01" in result.path


@pytest.mark.pds
@pytest.mark.asyncio
async def test_provincial_scraper_download_single_existing_valid(temp_output_dir):
    """Test download when file already exists and is valid."""
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    
    # Pre-create a valid file
    target_date = date(2026, 1, 15)
    filepath = scraper.get_file_path(target_date, DocumentType.BOLETIN, section=1)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(b"x" * 20000)  # Valid file
    
    result = await scraper.download_single(
        target_date=target_date,
        document_type=DocumentType.BOLETIN,
        section=1
    )
    
    assert result.status == "exists"
    assert result.filename == "20260115_1_Secc.pdf"


@pytest.mark.pds
@pytest.mark.asyncio
async def test_provincial_scraper_download_range_skip_weekends(temp_output_dir, mock_http_client):
    """Test download range with weekend skipping."""
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    scraper.config.skip_weekends = True
    scraper.config.sections = [1]
    scraper.config.rate_limit_delay = 0.01  # Fast for testing
    
    # Jan 4-5, 2026 is a weekend (Saturday-Sunday)
    start_date = date(2026, 1, 2)  # Friday
    end_date = date(2026, 1, 6)    # Tuesday
    
    with patch("httpx.AsyncClient", return_value=mock_http_client):
        results = await scraper.download_range(
            start_date=start_date,
            end_date=end_date,
            document_type=DocumentType.BOLETIN,
            sections=[1]
        )
    
    # Should have 3 results (Fri, Mon, Tue) - no weekend
    assert len(results) == 3
    
    # Verify no weekend dates
    for result in results:
        date_str = result.filename[:8]  # YYYYMMDD
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        file_date = date(year, month, day)
        assert file_date.weekday() < 5  # Monday = 0, Friday = 4


@pytest.mark.pds
def test_scraper_stats_tracking(sample_scraper_config):
    """Test that scraper statistics are tracked correctly."""
    scraper = ProvincialScraper(sample_scraper_config)
    
    # Initial stats
    stats = scraper.get_stats()
    assert stats["total_requested"] == 0
    assert stats["downloaded"] == 0
    assert stats["failed"] == 0
    
    # Simulate a successful download
    result = ScraperResult(
        filename="test.pdf",
        status="downloaded",
        size=1024
    )
    scraper._update_stats(result)
    
    stats = scraper.get_stats()
    assert stats["total_requested"] == 1
    assert stats["downloaded"] == 1
    assert stats["failed"] == 0
    
    # Simulate a failed download
    result_failed = ScraperResult(
        filename="test2.pdf",
        status="error",
        error="Test error"
    )
    scraper._update_stats(result_failed)
    
    stats = scraper.get_stats()
    assert stats["total_requested"] == 2
    assert stats["downloaded"] == 1
    assert stats["failed"] == 1
    assert len(stats["errors"]) == 1


@pytest.mark.pds
def test_provincial_scraper_get_available_sections():
    """Test getting available sections."""
    scraper = create_provincial_scraper()
    
    sections = scraper.get_available_sections()
    
    assert sections == [1, 2, 3, 4, 5]
    assert len(sections) == 5


@pytest.mark.pds
def test_create_provincial_scraper_factory():
    """Test provincial scraper factory function."""
    scraper = create_provincial_scraper(
        output_dir=Path("/custom/path")
    )
    
    assert isinstance(scraper, ProvincialScraper)
    assert scraper.config.output_dir == Path("/custom/path")


@pytest.mark.pds
def test_scraper_reset_stats():
    """Test resetting scraper statistics."""
    scraper = create_provincial_scraper()
    
    # Add some stats
    result = ScraperResult(filename="test.pdf", status="downloaded", size=1024)
    scraper._update_stats(result)
    
    assert scraper.get_stats()["downloaded"] == 1
    
    # Reset
    scraper.reset_stats()
    
    stats = scraper.get_stats()
    assert stats["total_requested"] == 0
    assert stats["downloaded"] == 0
    assert stats["failed"] == 0
    assert len(stats["errors"]) == 0
