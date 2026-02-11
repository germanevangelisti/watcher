"""
Unit tests for OEx (Output Execution) layer.

Tests alert dispatcher, report generator, and API gateway.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.services.alert_dispatcher import (
    AlertDispatcher,
    AlertPriority,
    AlertChannel,
    get_alert_dispatcher
)
from app.services.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    get_report_generator
)
from app.api.v1.api_gateway import APIGateway, get_gateway, GatewayRequest


# ============================================================================
# Alert Dispatcher Tests
# ============================================================================

@pytest.mark.oex
def test_alert_dispatcher_init():
    """Test AlertDispatcher initialization."""
    dispatcher = AlertDispatcher()
    
    assert dispatcher.alert_rules is not None
    assert dispatcher.stats["alerts_generated"] == 0
    assert dispatcher.stats["alerts_dispatched"] == 0


@pytest.mark.oex
@pytest.mark.asyncio
async def test_alert_create(sample_alert_data):
    """Test alert creation."""
    pytest.skip("Alert creation requires Alerta model - will be implemented")
    dispatcher = AlertDispatcher()
    
    result = await dispatcher.create_alert(
        title=sample_alert_data["title"],
        message=sample_alert_data["message"],
        priority=AlertPriority.HIGH,
        category=sample_alert_data["category"]
    )
    
    assert result["success"] is True
    assert "alert_id" in result
    assert result["priority"] == "high"


@pytest.mark.oex
@pytest.mark.asyncio
async def test_alert_dispatch_channels():
    """Test alert dispatch to multiple channels."""
    pytest.skip("Alert dispatch requires Alerta model - will be implemented")
    dispatcher = AlertDispatcher()
    
    # Create alert first
    create_result = await dispatcher.create_alert(
        title="Test Alert",
        message="Test message",
        priority=AlertPriority.HIGH
    )
    
    alert_id = create_result["alert_id"]
    
    # Dispatch to multiple channels
    dispatch_result = await dispatcher.dispatch_alert(
        alert_id=alert_id,
        channels=[AlertChannel.IN_APP, AlertChannel.EMAIL]
    )
    
    assert "channels_attempted" in dispatch_result
    assert dispatch_result["channels_attempted"] == 2


@pytest.mark.oex
def test_alert_priority_routing():
    """Test channel routing based on priority."""
    dispatcher = AlertDispatcher()
    
    # Critical priority
    channels_critical = dispatcher._get_channels_for_priority(AlertPriority.CRITICAL)
    assert AlertChannel.EMAIL in channels_critical
    assert AlertChannel.SMS in channels_critical
    
    # Low priority
    channels_low = dispatcher._get_channels_for_priority(AlertPriority.LOW)
    assert AlertChannel.IN_APP in channels_low
    assert AlertChannel.SMS not in channels_low


@pytest.mark.oex
@pytest.mark.asyncio
async def test_alert_create_and_dispatch():
    """Test combined create and dispatch operation."""
    pytest.skip("Alert create and dispatch requires Alerta model - will be implemented")
    dispatcher = AlertDispatcher()
    
    result = await dispatcher.create_and_dispatch(
        title="Combined Test",
        message="Test message",
        priority=AlertPriority.MEDIUM,
        category="test"
    )
    
    assert result["success"] is True
    assert "alert_id" in result
    assert "dispatched" in result


@pytest.mark.oex
def test_alert_dispatcher_stats():
    """Test alert dispatcher statistics tracking."""
    dispatcher = AlertDispatcher()
    
    initial_stats = dispatcher.get_stats()
    
    assert "alerts_generated" in initial_stats
    assert "alerts_dispatched" in initial_stats
    assert "by_priority" in initial_stats
    assert "by_channel" in initial_stats


@pytest.mark.oex
def test_alert_dispatcher_get_singleton():
    """Test getting singleton instance."""
    dispatcher1 = get_alert_dispatcher()
    dispatcher2 = get_alert_dispatcher()
    
    # Should be same instance
    assert dispatcher1 is dispatcher2


# ============================================================================
# Report Generator Tests
# ============================================================================

@pytest.mark.oex
def test_report_generator_init():
    """Test ReportGenerator initialization."""
    generator = ReportGenerator()
    
    assert generator.stats["reports_generated"] == 0
    assert len(generator.stats["by_type"]) > 0
    assert len(generator.stats["by_format"]) > 0


@pytest.mark.oex
@pytest.mark.asyncio
async def test_report_executive_summary(sample_report_data):
    """Test executive summary report generation."""
    generator = ReportGenerator()
    
    result = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data=sample_report_data,
        format=ReportFormat.JSON
    )
    
    assert result["success"] is True
    assert result["report_type"] == "executive_summary"
    assert "content" in result


@pytest.mark.oex
@pytest.mark.asyncio
async def test_report_format_json():
    """Test JSON report format."""
    generator = ReportGenerator()
    
    result = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data={"test": "data"},
        format=ReportFormat.JSON
    )
    
    assert result["format"] == "json"
    assert isinstance(result["content"], dict)


@pytest.mark.oex
@pytest.mark.asyncio
async def test_report_format_markdown():
    """Test Markdown report format."""
    generator = ReportGenerator()
    
    result = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data={
            "title": "Test Report",
            "summary": {"key": "value"},
            "highlights": ["Highlight 1", "Highlight 2"]
        },
        format=ReportFormat.MARKDOWN
    )
    
    assert result["format"] == "markdown"
    assert isinstance(result["content"], str)
    assert "#" in result["content"]  # Markdown header


@pytest.mark.oex
@pytest.mark.asyncio
async def test_report_format_html():
    """Test HTML report format."""
    generator = ReportGenerator()
    
    result = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data={"title": "Test Report"},
        format=ReportFormat.HTML
    )
    
    assert result["format"] == "html"
    assert isinstance(result["content"], str)
    assert "<html>" in result["content"]


@pytest.mark.oex
@pytest.mark.asyncio
async def test_report_detailed_analysis():
    """Test detailed analysis report."""
    generator = ReportGenerator()
    
    result = await generator.generate_report(
        report_type=ReportType.DETAILED_ANALYSIS,
        data={
            "scope": {"period": "2026-01"},
            "documents": [],
            "findings": []
        },
        format=ReportFormat.JSON
    )
    
    assert result["success"] is True
    assert result["report_type"] == "detailed_analysis"


@pytest.mark.oex
def test_report_generator_stats():
    """Test report generator statistics."""
    generator = ReportGenerator()
    
    stats = generator.get_stats()
    
    assert "reports_generated" in stats
    assert "by_type" in stats
    assert "by_format" in stats
    assert "errors" in stats


@pytest.mark.oex
def test_report_generator_get_singleton():
    """Test getting singleton instance."""
    gen1 = get_report_generator()
    gen2 = get_report_generator()
    
    assert gen1 is gen2


# ============================================================================
# API Gateway Tests
# ============================================================================

@pytest.mark.oex
def test_api_gateway_init():
    """Test APIGateway initialization."""
    gateway = APIGateway()
    
    assert gateway.service_registry is not None
    assert "pds" in gateway.service_registry
    assert "dia" in gateway.service_registry
    assert "kaa" in gateway.service_registry
    assert "oex" in gateway.service_registry


@pytest.mark.oex
@pytest.mark.asyncio
async def test_api_gateway_routing():
    """Test basic gateway routing."""
    gateway = APIGateway()
    
    request = GatewayRequest(
        service="oex",
        operation="create_alert",
        parameters={
            "title": "Test via Gateway",
            "message": "Test message",
            "priority": "low"
        }
    )
    
    result = await gateway.route_request(request)
    
    assert result.service == "oex"
    assert result.operation == "create_alert"


@pytest.mark.oex
@pytest.mark.asyncio
async def test_api_gateway_unknown_service():
    """Test gateway with unknown service."""
    gateway = APIGateway()
    
    request = GatewayRequest(
        service="unknown_service",
        operation="test_op",
        parameters={}
    )
    
    result = await gateway.route_request(request)
    
    assert result.success is False
    assert result.error is not None


@pytest.mark.oex
def test_api_gateway_stats():
    """Test gateway statistics tracking."""
    gateway = APIGateway()
    
    stats = gateway.get_stats()
    
    assert "total_requests" in stats
    assert "successful_requests" in stats
    assert "failed_requests" in stats
    assert "by_service" in stats


@pytest.mark.oex
def test_api_gateway_get_singleton():
    """Test getting singleton instance."""
    gw1 = get_gateway()
    gw2 = get_gateway()
    
    assert gw1 is gw2


@pytest.mark.oex
def test_api_gateway_service_registry():
    """Test service registry structure."""
    gateway = APIGateway()
    
    # Check PDS services
    assert "provincial" in gateway.service_registry["pds"]
    assert "municipal" in gateway.service_registry["pds"]
    
    # Check KAA services
    assert "knowledge_base" in gateway.service_registry["kaa"]
    assert "rag" in gateway.service_registry["kaa"]
    
    # Check OEx services
    assert "alerts" in gateway.service_registry["oex"]
    assert "reports" in gateway.service_registry["oex"]


# ============================================================================
# Integration Tests within OEx
# ============================================================================

@pytest.mark.oex
@pytest.mark.asyncio
async def test_alert_to_report_flow():
    """Test creating alert and then generating report about it."""
    pytest.skip("Alert creation requires Alerta model - will be implemented")
    dispatcher = AlertDispatcher()
    generator = ReportGenerator()
    
    # Create alert
    alert = await dispatcher.create_and_dispatch(
        title="High Risk Detected",
        message="Test alert",
        priority=AlertPriority.HIGH
    )
    
    # Generate report about alerts
    report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data={
            "alerts_generated": 1,
            "high_priority_alerts": 1
        },
        format=ReportFormat.JSON
    )
    
    assert alert["success"] is True
    assert report["success"] is True
