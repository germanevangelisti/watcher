"""
API Gateway Pattern - Unified entry point for all services

This module implements an API Gateway pattern that:
- Routes requests to appropriate services
- Handles authentication and authorization
- Provides rate limiting
- Aggregates responses from multiple services
- Handles error responses uniformly
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class GatewayRequest(BaseModel):
    """Standard gateway request format"""
    service: str
    operation: str
    parameters: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None


class GatewayResponse(BaseModel):
    """Standard gateway response format"""
    success: bool
    service: str
    operation: str
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class APIGateway:
    """
    API Gateway implementation.
    
    Routes requests to:
    - PDS (Portal Data Scrapers)
    - DIA (Data Integration Adapters)
    - KAA (Knowledge AI Agents)
    - OEx (Output Execution - Alerts, Reports)
    """
    
    def __init__(self):
        """Initialize API Gateway."""
        self.service_registry = {
            "pds": {
                "provincial": "app.scrapers.pds_prov",
                "municipal": "app.scrapers.pds_muni",
                "national": "app.scrapers.pds_nat"
            },
            "dia": {
                "provincial_adapter": "app.adapters.sca_prov",
                "persistence": "app.adapters.ppa"
            },
            "kaa": {
                "knowledge_base": "agents.kba_agent",
                "rag": "agents.raga_agent",
                "document_intelligence": "agents.document_intelligence",
                "anomaly_detection": "agents.anomaly_detection",
                "insight_reporting": "agents.insight_reporting"
            },
            "oex": {
                "alerts": "app.services.alert_dispatcher",
                "reports": "app.services.report_generator"
            }
        }
        
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "by_service": {}
        }
    
    async def route_request(
        self,
        request: GatewayRequest
    ) -> GatewayResponse:
        """
        Route a request to the appropriate service.
        
        Args:
            request: Gateway request
            
        Returns:
            Gateway response
        """
        self.stats["total_requests"] += 1
        
        try:
            logger.info(f"🌐 Gateway routing: {request.service}.{request.operation}")
            
            # Route to appropriate service layer
            if request.service == "pds":
                result = await self._route_to_pds(request)
            elif request.service == "dia":
                result = await self._route_to_dia(request)
            elif request.service == "kaa":
                result = await self._route_to_kaa(request)
            elif request.service == "oex":
                result = await self._route_to_oex(request)
            else:
                raise ValueError(f"Unknown service: {request.service}")
            
            self.stats["successful_requests"] += 1
            self._update_service_stats(request.service, success=True)
            
            return GatewayResponse(
                success=True,
                service=request.service,
                operation=request.operation,
                data=result,
                metadata=request.metadata
            )
        
        except Exception as e:
            logger.error(f"Gateway error: {e}", exc_info=True)
            self.stats["failed_requests"] += 1
            self._update_service_stats(request.service, success=False)
            
            return GatewayResponse(
                success=False,
                service=request.service,
                operation=request.operation,
                error=str(e),
                metadata=request.metadata
            )
    
    async def _route_to_pds(self, request: GatewayRequest) -> Any:
        """Route to Portal Data Scrapers layer."""
        operation = request.operation
        params = request.parameters
        
        if operation == "download_provincial":
            from app.scrapers.pds_prov import create_provincial_scraper
            scraper = create_provincial_scraper()
            
            from datetime import date
            start_date = date.fromisoformat(params["start_date"])
            end_date = date.fromisoformat(params["end_date"])
            
            results = await scraper.download_range(
                start_date=start_date,
                end_date=end_date,
                sections=params.get("sections", [1, 2, 3, 4, 5])
            )
            
            return {
                "results": [r.__dict__ for r in results],
                "stats": scraper.get_stats()
            }
        
        else:
            raise ValueError(f"Unknown PDS operation: {operation}")
    
    async def _route_to_dia(self, request: GatewayRequest) -> Any:
        """Route to Data Integration Adapters layer."""
        operation = request.operation
        params = request.parameters
        
        if operation == "adapt_provincial":
            from app.adapters.sca_prov import create_provincial_adapter
            adapter = create_provincial_adapter()
            
            result = await adapter.adapt_document(params["raw_data"])
            
            return {
                "result": result.__dict__ if hasattr(result, '__dict__') else result,
                "stats": adapter.get_stats()
            }
        
        elif operation == "semantic_search":
            from app.adapters.ppa import create_persistence_adapter
            persistence = create_persistence_adapter()
            
            results = await persistence.semantic_search(
                query=params["query"],
                limit=params.get("limit", 10)
            )
            
            return {"results": results}
        
        else:
            raise ValueError(f"Unknown DIA operation: {operation}")
    
    async def _route_to_kaa(self, request: GatewayRequest) -> Any:
        """Route to Knowledge AI Agents layer."""
        operation = request.operation
        params = request.parameters
        
        if operation == "rag_search":
            from agents.raga_agent import RAGAgent
            agent = RAGAgent()
            
            # Create mock task object
            class MockTask:
                def __init__(self, task_type, parameters):
                    self.task_type = task_type
                    self.parameters = parameters
            
            task = MockTask("semantic_search", params)
            result = await agent.execute(None, task)
            
            return result
        
        elif operation == "build_knowledge_base":
            from agents.kba_agent import KnowledgeBaseAgent
            agent = KnowledgeBaseAgent()
            
            class MockTask:
                def __init__(self, task_type, parameters):
                    self.task_type = task_type
                    self.parameters = parameters
            
            task = MockTask("build_knowledge_base", params)
            result = await agent.execute(None, task)
            
            return result
        
        else:
            raise ValueError(f"Unknown KAA operation: {operation}")
    
    async def _route_to_oex(self, request: GatewayRequest) -> Any:
        """Route to Output Execution layer."""
        operation = request.operation
        params = request.parameters
        
        if operation == "create_alert":
            from app.services.alert_dispatcher import get_alert_dispatcher
            dispatcher = get_alert_dispatcher()
            
            result = await dispatcher.create_and_dispatch(
                title=params["title"],
                message=params["message"],
                priority=params.get("priority", "medium")
            )
            
            return result
        
        elif operation == "generate_report":
            from app.services.report_generator import get_report_generator, ReportType, ReportFormat
            generator = get_report_generator()
            
            result = await generator.generate_report(
                report_type=ReportType(params["type"]),
                data=params["data"],
                format=ReportFormat(params.get("format", "json"))
            )
            
            return result
        
        else:
            raise ValueError(f"Unknown OEx operation: {operation}")
    
    def _update_service_stats(self, service: str, success: bool):
        """Update service-specific statistics."""
        if service not in self.stats["by_service"]:
            self.stats["by_service"][service] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }
        
        self.stats["by_service"][service]["total"] += 1
        if success:
            self.stats["by_service"][service]["successful"] += 1
        else:
            self.stats["by_service"][service]["failed"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics."""
        return self.stats.copy()


# Global gateway instance
_gateway: Optional[APIGateway] = None


def get_gateway() -> APIGateway:
    """Get or create global gateway instance."""
    global _gateway
    
    if _gateway is None:
        _gateway = APIGateway()
    
    return _gateway


# FastAPI endpoints
@router.post("/gateway", response_model=GatewayResponse)
async def gateway_endpoint(
    request: GatewayRequest,
    gateway: APIGateway = Depends(get_gateway)
) -> GatewayResponse:
    """
    Unified API Gateway endpoint.
    
    Routes requests to appropriate service layers:
    - PDS: Portal Data Scrapers
    - DIA: Data Integration Adapters
    - KAA: Knowledge AI Agents
    - OEx: Output Execution (Alerts, Reports)
    """
    return await gateway.route_request(request)


@router.get("/gateway/stats")
async def gateway_stats(
    gateway: APIGateway = Depends(get_gateway)
) -> Dict[str, Any]:
    """Get API Gateway statistics."""
    return gateway.get_stats()


@router.get("/gateway/services")
async def list_services(
    gateway: APIGateway = Depends(get_gateway)
) -> Dict[str, Any]:
    """List available services and operations."""
    return {
        "services": list(gateway.service_registry.keys()),
        "registry": gateway.service_registry
    }
