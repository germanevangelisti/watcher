"""
Integration tests for API Gateway.

Tests routing to all service layers through unified gateway.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
sys.path.insert(0, str(backend_path))

from app.api.v1.api_gateway import APIGateway, GatewayRequest


# ============================================================================
# API Gateway Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_route_to_kaa():
    """Test routing KAA operations through gateway."""
    gateway = APIGateway()
    
    request = GatewayRequest(
        service="kaa",
        operation="rag_search",
        parameters={
            "query": "test search",
            "limit": 5
        }
    )
    
    result = await gateway.route_request(request)
    
    assert result.service == "kaa"
    assert result.operation == "rag_search"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_route_to_oex_alerts():
    """Test routing alert creation through gateway."""
    gateway = APIGateway()
    
    request = GatewayRequest(
        service="oex",
        operation="create_alert",
        parameters={
            "title": "Gateway Test Alert",
            "message": "Test via gateway",
            "priority": "medium"
        }
    )
    
    result = await gateway.route_request(request)
    
    assert result.service == "oex"
    assert result.operation == "create_alert"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_route_to_oex_reports():
    """Test routing report generation through gateway."""
    gateway = APIGateway()
    
    request = GatewayRequest(
        service="oex",
        operation="generate_report",
        parameters={
            "type": "executive_summary",
            "format": "json",
            "data": {
                "period": "Test",
                "total_documents": 10
            }
        }
    )
    
    result = await gateway.route_request(request)
    
    assert result.service == "oex"
    assert result.operation == "generate_report"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_stats_tracking():
    """Test that gateway tracks statistics across requests."""
    gateway = APIGateway()
    
    initial_stats = gateway.get_stats()
    initial_total = initial_stats["total_requests"]
    
    # Make a request
    request = GatewayRequest(
        service="oex",
        operation="create_alert",
        parameters={
            "title": "Stats Test",
            "message": "Test",
            "priority": "low"
        }
    )
    
    await gateway.route_request(request)
    
    new_stats = gateway.get_stats()
    
    assert new_stats["total_requests"] >= initial_total
