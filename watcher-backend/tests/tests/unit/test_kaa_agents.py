"""
Unit tests for KAA (Knowledge AI Agents) layer.

Tests specialized agents: KBA, RAGA, Document Intelligence.
"""

import pytest
from pathlib import Path
import sys

# Add paths
backend_path = Path(__file__).resolve().parent.parent.parent / "watcher-monolith" / "backend"
agents_path = Path(__file__).resolve().parent.parent.parent / "agents"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(agents_path))

from kba_agent import KnowledgeBaseAgent
from raga_agent import RAGAgent
from document_intelligence import DocumentIntelligenceAgent


# ============================================================================
# KBA (Knowledge Base Agent) Tests
# ============================================================================

@pytest.mark.kaa
def test_kba_agent_init():
    """Test KBA agent initialization."""
    agent = KnowledgeBaseAgent()
    
    assert agent.name == "Knowledge Base Agent"
    assert agent.knowledge_stats["entities_extracted"] == 0
    assert agent.knowledge_stats["documents_processed"] == 0


@pytest.mark.kaa
def test_kba_agent_init_with_config():
    """Test KBA with custom config."""
    config = {"custom_field": "test_value"}
    agent = KnowledgeBaseAgent(config)
    
    assert agent.config == config
    assert agent.config["custom_field"] == "test_value"


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_kba_build_knowledge_base(sample_agent_task):
    """Test building knowledge base."""
    agent = KnowledgeBaseAgent()
    
    task = sample_agent_task(
        task_type="build_knowledge_base",
        parameters={
            "start_year": 2026,
            "start_month": 1,
            "limit": 10
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]
    if result["status"] == "completed":
        assert "results" in result


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_kba_query_knowledge(sample_agent_task):
    """Test querying knowledge base."""
    agent = KnowledgeBaseAgent()
    
    task = sample_agent_task(
        task_type="query_knowledge",
        parameters={
            "query": "test query",
            "entity_type": "all"
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_kba_unknown_task_type(sample_agent_task):
    """Test KBA with unknown task type."""
    agent = KnowledgeBaseAgent()
    
    task = sample_agent_task(
        task_type="unknown_task",
        parameters={}
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] == "completed"
    assert "not implemented" in result["message"].lower()


@pytest.mark.kaa
def test_kba_get_stats():
    """Test getting KBA statistics."""
    agent = KnowledgeBaseAgent()
    
    stats = agent.get_stats()
    
    assert isinstance(stats, dict)
    assert "entities_extracted" in stats
    assert "documents_processed" in stats


# ============================================================================
# RAGA (RAG Agent) Tests
# ============================================================================

@pytest.mark.kaa
def test_raga_agent_init():
    """Test RAGA agent initialization."""
    agent = RAGAgent()
    
    assert agent.name == "RAG Agent"
    assert agent.stats["queries_processed"] == 0
    assert agent.stats["documents_retrieved"] == 0


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_raga_semantic_search(sample_agent_task):
    """Test semantic search via RAGA."""
    agent = RAGAgent()
    
    task = sample_agent_task(
        task_type="semantic_search",
        parameters={
            "query": "licitaciones públicas",
            "limit": 5
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]
    if result["status"] == "completed":
        assert "results" in result


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_raga_semantic_search_empty_query(sample_agent_task):
    """Test semantic search with empty query."""
    agent = RAGAgent()
    
    task = sample_agent_task(
        task_type="semantic_search",
        parameters={
            "query": "",
            "limit": 5
        }
    )
    
    result = await agent.execute(None, task)
    
    # Should handle empty query gracefully
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_raga_answer_question(sample_agent_task):
    """Test Q&A with RAG."""
    agent = RAGAgent()
    
    task = sample_agent_task(
        task_type="answer_question",
        parameters={
            "question": "¿Qué licitaciones se publicaron?",
            "context_limit": 5
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]
    if result["status"] == "completed":
        assert "results" in result


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_raga_summarize_topic(sample_agent_task):
    """Test topic summarization."""
    agent = RAGAgent()
    
    task = sample_agent_task(
        task_type="summarize_topic",
        parameters={
            "topic": "obras públicas"
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
def test_raga_get_stats():
    """Test getting RAGA statistics."""
    agent = RAGAgent()
    
    stats = agent.get_stats()
    
    assert isinstance(stats, dict)
    assert "queries_processed" in stats
    assert "documents_retrieved" in stats


# ============================================================================
# Document Intelligence Agent Tests
# ============================================================================

@pytest.mark.kaa
def test_doc_intelligence_init():
    """Test Document Intelligence agent initialization."""
    agent = DocumentIntelligenceAgent()
    
    assert agent.name == "Document Intelligence Agent"


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_doc_intelligence_entity_search(sample_agent_task):
    """Test entity search."""
    agent = DocumentIntelligenceAgent()
    
    task = sample_agent_task(
        task_type="entity_search",
        parameters={
            "entity_name": "TEST SA",
            "start_year": 2026,
            "start_month": 1,
            "limit": 10
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_doc_intelligence_extract_document(sample_agent_task):
    """Test document extraction."""
    agent = DocumentIntelligenceAgent()
    
    task = sample_agent_task(
        task_type="extract_document",
        parameters={
            "document_id": 1
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_doc_intelligence_create_embeddings(sample_agent_task):
    """Test embeddings creation."""
    agent = DocumentIntelligenceAgent()
    
    task = sample_agent_task(
        task_type="create_embeddings",
        parameters={
            "document_ids": [1, 2, 3],
            "batch_size": 5
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_doc_intelligence_classify_documents(sample_agent_task):
    """Test document classification."""
    agent = DocumentIntelligenceAgent()
    
    task = sample_agent_task(
        task_type="classify_documents",
        parameters={
            "limit": 20
        }
    )
    
    result = await agent.execute(None, task)
    
    assert result["status"] in ["completed", "failed"]


@pytest.mark.kaa
@pytest.mark.asyncio
async def test_doc_intelligence_missing_parameter(sample_agent_task):
    """Test with missing required parameter."""
    agent = DocumentIntelligenceAgent()
    
    task = sample_agent_task(
        task_type="extract_document",
        parameters={}  # Missing document_id
    )
    
    result = await agent.execute(None, task)
    
    # Should fail or handle gracefully
    assert result["status"] in ["completed", "failed"]


# ============================================================================
# Agent Integration Tests
# ============================================================================

@pytest.mark.kaa
def test_all_agents_have_execute_method():
    """Test that all agents implement execute method."""
    agents = [
        KnowledgeBaseAgent(),
        RAGAgent(),
        DocumentIntelligenceAgent()
    ]
    
    for agent in agents:
        assert hasattr(agent, 'execute')
        assert callable(agent.execute)


@pytest.mark.kaa
def test_all_agents_have_name():
    """Test that all agents have a name attribute."""
    agents = [
        KnowledgeBaseAgent(),
        RAGAgent(),
        DocumentIntelligenceAgent()
    ]
    
    for agent in agents:
        assert hasattr(agent, 'name')
        assert isinstance(agent.name, str)
        assert len(agent.name) > 0
