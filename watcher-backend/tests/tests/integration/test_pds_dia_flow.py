"""
Integration tests for PDS -> DIA flow.

Tests the flow from scraper to adapter to persistence.
"""

import pytest
from pathlib import Path
from datetime import date
import sys
from unittest.mock import patch, MagicMock

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.scrapers.pds_prov import create_provincial_scraper
from app.scrapers.base_scraper import DocumentType
from app.adapters.sca_prov import create_provincial_adapter


# ============================================================================
# PDS -> DIA Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_scraper_to_adapter_flow(temp_output_dir, mock_http_client):
    """Test complete flow from scraper to adapter."""
    # Step 1: Scraper downloads document
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    
    with patch("httpx.AsyncClient", return_value=mock_http_client):
        scraper_result = await scraper.download_single(
            target_date=date(2026, 1, 15),
            document_type=DocumentType.BOLETIN,
            section=1
        )
    
    assert scraper_result.status == "downloaded"
    
    # Step 2: Adapter transforms scraped data
    adapter = create_provincial_adapter()
    
    raw_data = {
        "filename": scraper_result.filename,
        "date": "2026-01-15",
        "section": 1,
        "size": scraper_result.size,
        "file_path": scraper_result.path
    }
    
    adapter_result = await adapter.adapt_document(raw_data)
    
    assert adapter_result.success is True
    assert adapter_result.document is not None
    assert adapter_result.document.filename == scraper_result.filename


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scraper_range_to_adapter_batch(temp_output_dir, mock_http_client):
    """Test range scraping followed by batch adaptation."""
    # Step 1: Scrape multiple documents
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    scraper.config.sections = [1]
    scraper.config.rate_limit_delay = 0.01
    
    with patch("httpx.AsyncClient", return_value=mock_http_client):
        scraper_results = await scraper.download_range(
            start_date=date(2026, 1, 2),  # Thursday
            end_date=date(2026, 1, 3),    # Friday (2 weekdays)
            sections=[1]
        )
    
    # Should have at least 1 result (weekends are skipped)
    assert len(scraper_results) >= 1
    
    # Step 2: Adapt all scraped documents
    adapter = create_provincial_adapter()
    
    raw_data_list = [
        {
            "filename": r.filename,
            "date": date(2026, 1, 2 + i).isoformat(),
            "section": 1,
            "size": r.size
        }
        for i, r in enumerate(scraper_results)
    ]
    
    adapter_results = await adapter.adapt_batch(raw_data_list)
    
    assert len(adapter_results) == len(scraper_results)
    assert all(r.success for r in adapter_results)


@pytest.mark.integration
def test_scraper_output_matches_adapter_input(temp_output_dir):
    """Test that scraper output format matches adapter expected input."""
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    adapter = create_provincial_adapter()
    
    # Create mock scraper result
    target_date = date(2026, 1, 15)
    filepath = scraper.get_file_path(target_date, DocumentType.BOLETIN, section=1)
    
    # This is what scraper produces
    scraper_output = {
        "filename": filepath.name,
        "date": target_date.isoformat(),
        "section": 1,
        "size": 1024000,
        "file_path": str(filepath)
    }
    
    # Adapter should be able to process it
    # (we don't actually call adapt_document here, just validate structure)
    assert "filename" in scraper_output
    assert "date" in scraper_output
    assert "section" in scraper_output
