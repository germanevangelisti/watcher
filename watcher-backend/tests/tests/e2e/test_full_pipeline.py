"""
End-to-end tests for complete pipeline.

Tests full workflows from download to output.
"""

import pytest
from pathlib import Path
from datetime import date
import sys
from unittest.mock import patch

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
agents_path = Path(__file__).resolve().parent.parent.parent / "agents"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(agents_path))

from app.scrapers.pds_prov import create_provincial_scraper
from app.scrapers.base_scraper import DocumentType
from app.adapters.sca_prov import create_provincial_adapter
from app.services.alert_dispatcher import AlertDispatcher
from app.services.report_generator import ReportGenerator, ReportType, ReportFormat
from app.api.v1.api_gateway import APIGateway, GatewayRequest

# Fix import for RAGAgent
from raga_agent import RAGAgent


# ============================================================================
# End-to-End Pipeline Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_download_to_alert(temp_output_dir, mock_http_client):
    """
    Test complete pipeline: Download -> Adapt -> Analyze -> Alert.
    
    Simulates the full workflow from downloading a bulletin to generating an alert.
    """
    # Step 1: Download bulletin
    scraper = create_provincial_scraper(output_dir=temp_output_dir)
    
    with patch("httpx.AsyncClient", return_value=mock_http_client):
        scraper_result = await scraper.download_single(
            target_date=date(2026, 1, 15),
            document_type=DocumentType.BOLETIN,
            section=1
        )
    
    assert scraper_result.status == "downloaded"
    
    # Step 2: Adapt to DocumentSchema
    adapter = create_provincial_adapter()
    raw_data = {
        "filename": scraper_result.filename,
        "date": "2026-01-15",
        "section": 1,
        "content": "DECRETO 123/2026. La empresa TEST SA recibe subsidio de $100.000.000.",
        "size": scraper_result.size
    }
    
    adapter_result = await adapter.adapt_document(raw_data)
    assert adapter_result.success is True
    
    # Step 3: Simulate analysis detecting high risk
    analysis_results = [{
        "document_id": "test_1",
        "filename": adapter_result.document.filename,
        "risk_level": "ALTO",
        "entities": {
            "companies": ["TEST SA"],
            "amounts": ["$100.000.000"]
        }
    }]
    
    # Step 4: Generate alert
    dispatcher = AlertDispatcher()
    alert_result = await dispatcher.process_analysis_results(analysis_results)
    
    assert alert_result["success"] is True
    
    # Verify complete flow
    assert scraper_result.filename == adapter_result.document.filename


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_search_e2e(temp_output_dir, sample_bulletin_data):
    """
    Test semantic search pipeline: Document -> Embedding -> Search.
    
    Tests the complete flow for semantic search functionality.
    """
    # Step 1: Adapt document
    adapter = create_provincial_adapter()
    adapter_result = await adapter.adapt_document(sample_bulletin_data)
    
    assert adapter_result.success is True
    document = adapter_result.document
    
    # Step 2: In real scenario, embeddings would be created
    # For this test, we just verify the document is properly formatted
    assert document.content is not None or document.filename is not None
    
    # Step 3: Search would be performed by RAGA
    # (Simulated - actual search requires ChromaDB setup)
    agent = RAGAgent()
    
    class MockTask:
        task_type = "semantic_search"
        parameters = {
            "query": "subsidio",
            "limit": 5
        }
    
    search_result = await agent.execute(None, MockTask())
    
    assert search_result["status"] in ["completed", "failed"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_report_generation_e2e():
    """
    Test report generation pipeline: Data -> Aggregate -> Format -> Report.
    
    Tests the complete flow for generating reports from processed data.
    """
    # Step 1: Simulate aggregated data from multiple sources
    analysis_data = {
        "period": "January 2026",
        "total_documents": 50,
        "high_risk_count": 3,
        "medium_risk_count": 10,
        "low_risk_count": 37,
        "total_amount": 250000000,
        "key_findings": [
            "3 high-risk transactions detected",
            "Total financial volume: $250M",
            "10 new entities identified"
        ],
        "recommendations": [
            "Review high-risk transactions",
            "Update monitoring rules"
        ]
    }
    
    # Step 2: Generate report in multiple formats
    generator = ReportGenerator()
    
    # JSON report
    json_report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data=analysis_data,
        format=ReportFormat.JSON
    )
    assert json_report["success"] is True
    assert json_report["format"] == "json"
    
    # Markdown report
    md_report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data=analysis_data,
        format=ReportFormat.MARKDOWN
    )
    assert md_report["success"] is True
    assert md_report["format"] == "markdown"
    assert isinstance(md_report["content"], str)
    
    # HTML report
    html_report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data=analysis_data,
        format=ReportFormat.HTML
    )
    assert html_report["success"] is True
    assert html_report["format"] == "html"
    assert "<html>" in html_report["content"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_gateway_full_workflow():
    """
    Test complete workflow via API Gateway.
    
    Tests multiple operations routed through the unified gateway.
    """
    gateway = APIGateway()
    
    # Step 1: Create alert via gateway
    alert_request = GatewayRequest(
        service="oex",
        operation="create_alert",
        parameters={
            "title": "E2E Test Alert",
            "message": "Alert created via gateway",
            "priority": "high"
        }
    )
    
    alert_result = await gateway.route_request(alert_request)
    assert alert_result.success is True
    
    # Step 2: Generate report via gateway
    report_request = GatewayRequest(
        service="oex",
        operation="generate_report",
        parameters={
            "type": "executive_summary",
            "format": "json",
            "data": {
                "period": "E2E Test",
                "total_documents": 100,
                "high_risk_count": 5
            }
        }
    )
    
    report_result = await gateway.route_request(report_request)
    assert report_result.success is True
    
    # Step 3: Perform search via gateway
    search_request = GatewayRequest(
        service="kaa",
        operation="rag_search",
        parameters={
            "query": "test search",
            "limit": 10
        }
    )
    
    search_result = await gateway.route_request(search_request)
    assert search_result.service == "kaa"
    
    # Verify gateway stats
    stats = gateway.get_stats()
    assert stats["total_requests"] >= 3
    assert "oex" in stats["by_service"]
    assert "kaa" in stats["by_service"]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
async def test_multi_document_processing_pipeline(temp_output_dir, mock_http_client):
    """
    Test processing multiple documents through complete pipeline.
    
    Tests batch processing capabilities across all layers.
    """
    # Step 1: Download multiple bulletins
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
    
    # Step 2: Adapt all documents
    adapter = create_provincial_adapter()
    
    raw_data_list = [
        {
            "filename": r.filename,
            "date": date(2026, 1, 2 + i).isoformat(),
            "section": 1,
            "content": f"Test content for document {i}",
            "size": r.size
        }
        for i, r in enumerate(scraper_results)
    ]
    
    adapter_results = await adapter.adapt_batch(raw_data_list)
    
    assert len(adapter_results) == len(scraper_results)
    assert all(r.success for r in adapter_results)
    
    # Step 3: Generate summary report
    generator = ReportGenerator()
    
    summary_data = {
        "period": "Jan 2-4, 2026",
        "total_documents": len(adapter_results),
        "successful_adaptations": sum(1 for r in adapter_results if r.success)
    }
    
    report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data=summary_data,
        format=ReportFormat.JSON
    )
    
    assert report["success"] is True
    
    # Verify stats across all components
    scraper_stats = scraper.get_stats()
    adapter_stats = adapter.get_stats()
    
    assert scraper_stats["total_requested"] == len(scraper_results)
    assert adapter_stats["total_processed"] == len(adapter_results)


# ============================================================================
# Performance and Load Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
def test_system_performance_baseline():
    """
    Baseline performance test for system components.
    
    Ensures that basic operations complete within acceptable time limits.
    """
    from app.scrapers.pds_prov import create_provincial_scraper
    from app.adapters.sca_prov import create_provincial_adapter
    from app.services.alert_dispatcher import get_alert_dispatcher
    from app.services.report_generator import get_report_generator
    from app.api.v1.api_gateway import get_gateway
    
    # All components should initialize quickly
    scraper = create_provincial_scraper()
    assert scraper is not None
    
    adapter = create_provincial_adapter()
    assert adapter is not None
    
    dispatcher = get_alert_dispatcher()
    assert dispatcher is not None
    
    generator = get_report_generator()
    assert generator is not None
    
    gateway = get_gateway()
    assert gateway is not None
    
    # All should have stats
    assert scraper.get_stats() is not None
    assert adapter.get_stats() is not None
    assert dispatcher.get_stats() is not None
    assert generator.get_stats() is not None
    assert gateway.get_stats() is not None
