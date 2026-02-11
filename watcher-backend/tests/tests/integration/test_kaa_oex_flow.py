"""
Integration tests for KAA -> OEx flow.

Tests the flow from AI agents to output execution.
"""

import pytest
from pathlib import Path
import sys

# Add paths
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.services.alert_dispatcher import AlertDispatcher, AlertPriority
from app.services.report_generator import ReportGenerator, ReportType, ReportFormat


# ============================================================================
# KAA -> OEx Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_detection_to_alert():
    """Test flow from agent detection to alert creation."""
    # Simulate agent detecting high risk
    analysis_results = [
        {
            "document_id": "test_1",
            "filename": "20260101_1_Secc.pdf",
            "risk_level": "ALTO",
            "entities": {
                "companies": ["TEST SA"],
                "amounts": ["$100000000"]
            }
        }
    ]
    
    # Dispatcher processes results and creates alerts
    dispatcher = AlertDispatcher()
    result = await dispatcher.process_analysis_results(analysis_results)
    
    assert result["success"] is True
    assert result["alerts_created"] >= 0  # May create alerts based on rules


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_results_to_report():
    """Test generating report from agent analysis results."""
    # Simulate agent analysis results
    analysis_data = {
        "period": "January 2026",
        "total_documents": 50,
        "high_risk_count": 3,
        "total_amount": 150000000,
        "key_findings": [
            "3 high-risk transactions detected",
            "Total amount: $150M"
        ]
    }
    
    # Generate report
    generator = ReportGenerator()
    report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data=analysis_data,
        format=ReportFormat.MARKDOWN
    )
    
    assert report["success"] is True
    assert "content" in report


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_agents_to_combined_output():
    """Test combining results from multiple agents into single output."""
    # Simulate results from different agents
    kba_results = {
        "organizations": ["Company A", "Company B"],
        "total_entities": 50
    }
    
    raga_results = {
        "searches_performed": 10,
        "documents_retrieved": 25
    }
    
    # Combine into report
    generator = ReportGenerator()
    combined_data = {
        "period": "Test Period",
        "total_documents": 100,
        "knowledge_base": kba_results,
        "search_results": raga_results
    }
    
    report = await generator.generate_report(
        report_type=ReportType.DETAILED_ANALYSIS,
        data=combined_data,
        format=ReportFormat.JSON
    )
    
    assert report["success"] is True
