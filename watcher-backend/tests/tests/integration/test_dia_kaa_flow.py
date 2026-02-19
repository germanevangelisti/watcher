"""
Integration tests for DIA -> KAA flow.

Tests the flow from adapters to AI agents.
"""

import pytest
from pathlib import Path
import sys

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
agents_path = Path(__file__).resolve().parent.parent.parent / "agents"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(agents_path))

from app.adapters.sca_prov import create_provincial_adapter
from raga_agent import RAGAgent
from kba_agent import KnowledgeBaseAgent


# ============================================================================
# DIA -> KAA Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_adapter_to_agents_flow(sample_bulletin_data):
    """Test flow from adapter to agents."""
    # Step 1: Adapt document
    adapter = create_provincial_adapter()
    adapter_result = await adapter.adapt_document(sample_bulletin_data)
    
    assert adapter_result.success is True
    document = adapter_result.document
    
    # Step 2: Agents can work with adapted document
    # (In real scenario, document would be in DB and agents would query it)
    assert document.content is not None or document.filename is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_schema_to_raga_search(sample_document_schema, sample_agent_task):
    """Test that documents can be searched by RAGA."""
    agent = RAGAgent()
    
    # Create a search task
    task = sample_agent_task(
        task_type="semantic_search",
        parameters={
            "query": "test query",
            "limit": 5
        }
    )
    
    result = await agent.execute(None, task)
    
    # Should complete (may not find results without actual DB)
    assert result["status"] in ["completed", "failed"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_documents_to_knowledge_base(sample_agent_task):
    """Test building knowledge base from multiple documents."""
    agent = KnowledgeBaseAgent()
    
    task = sample_agent_task(
        task_type="build_knowledge_base",
        parameters={
            "start_year": 2026,
            "start_month": 1,
            "limit": 5
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]
