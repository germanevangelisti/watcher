"""
Test E2E: Adversarial Verification Pipeline
5 boletines del 02/01/2026 — Fases I, II, III, IV, V

Objetivo: VCP > 0.85 procesando datos reales de los boletines base.
Mocks: Gemini/VertexAI (CI cost limits). Servicios de dominio: reales.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# ── path setup ────────────────────────────────────────────────────────────────
BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND))

# ── fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_BOLETIN_TEXT = """
DECRETO 2026/RSIHG-00000001
El Gobierno de la Provincia de Córdoba, en ejercicio de sus facultades,
DECRETA:
ARTÍCULO 1°.- Apruébase la contratación directa con la empresa CONSTRUCTORA NORTE SA
por un monto de $1.500.000 (un millón quinientos mil pesos) para la obra de
refacción del edificio ubicado en Avenida Colón 1234.
ARTÍCULO 2°.- Los fondos provendrán del Ministerio de Obras Públicas de Córdoba.
ARTÍCULO 3°.- Regístrese y comuníquese.

RESOLUCIÓN 2026/RSIHG-00000042
El Ministerio de Economía de Córdoba, visto el Expediente EX-2026-00001234,
RESUELVE:
ARTÍCULO 1°.- Adjudícase la LICITACIÓN PÚBLICA N° 001/2026 a la firma TECH SOLUTIONS SRL
por la suma de $3.200.000 (tres millones doscientos mil pesos), para provisión de equipos
informáticos.
ARTÍCULO 2°.- Impútese el gasto al presupuesto del Ministerio de Economía de Córdoba.

DECRETO 2026/RSIHG-00000099
La Secretaría de Gestión Pública de Córdoba,
DECRETA:
ARTÍCULO 1°.- Desígnase a la Lic. MARÍA FERNÁNDEZ en el cargo de Directora de la Dirección
de Recursos Humanos dependiente del Ministerio de Gobierno de Córdoba.
ARTÍCULO 2°.- Comuníquese y archívese.
"""

SAMPLE_ACTO = {
    "tipo_acto": "decreto",
    "numero": "2026/RSIHG-00000001",
    "organismo": "Ministerio de Obras Públicas de Córdoba",
    "beneficiarios": ["CONSTRUCTORA NORTE SA"],
    "montos": ["$1.500.000"],
    "monto_total_numerico": 1500000.0,
    "descripcion": "Contratación directa para refacción de edificio en Avenida Colón 1234",
    "texto_original": "Apruébase la contratación directa con la empresa CONSTRUCTORA NORTE SA",
    "riesgo": "medio",
    "motivo_riesgo": "Contratación directa con monto significativo",
    "accion_sugerida": "Verificar proceso de selección",
    # Nuevos campos de detección mejorada
    "fecha_acto": "15 de febrero de 2026",
    "expediente": "EX-2026-00001234-GCBA-MOP",
    "referencias_normativas": ["Ley N° 8614", "Decreto 272/95"],
    "fechas_clave": ["vigencia desde: 01/03/2026"],
    "relacion_principal": "Ministerio de Obras Públicas adjudica contratación directa a CONSTRUCTORA NORTE SA por $1.500.000",
    "firmante": "Ing. Roberto García, Ministro de Obras Públicas",
    "imputacion_presupuestaria": "Programa 14 - Actividad 3 - Inciso 4 - ejercicio 2026",
    "presupuesto_oficial": 0,
}


def _make_mock_search_result(text: str, score: float = 0.85):
    """Build a SearchResult-like mock."""
    r = MagicMock()
    r.text = text
    r.score = score
    r.document_id = "doc_test"
    r.chunk_id = "chunk_0"
    return r


# ── unit-level: Fase I (Entity Anchoring) ────────────────────────────────────

class TestEntityAnchoring:
    def test_build_entity_map_finds_positions(self):
        from app.services.entity_service import EntityService, EntityResult
        svc = EntityService()
        entities = svc.extract_entities(SAMPLE_BOLETIN_TEXT)
        assert len(entities) > 0, "Should extract at least one entity"

        entity_map = svc.build_entity_map(entities, SAMPLE_BOLETIN_TEXT)
        # EntityMap should have entries
        assert len(entity_map._entries) > 0, "EntityMap should have positional entries"

    def test_entity_map_get_in_range(self):
        from app.services.entity_service import EntityService, EntityMap, EntityResult
        from dataclasses import dataclass

        svc = EntityService()
        text = SAMPLE_BOLETIN_TEXT
        entities = svc.extract_entities(text)
        em = svc.build_entity_map(entities, text)

        # Query a wide range — should return some entities
        found = em.get_entities_in_range(0, len(text))
        assert found is not None  # list (possibly empty for narrow range, but not error)

    def test_chunking_with_entity_map_no_error(self):
        from app.services.entity_service import EntityService
        from app.services.chunking_service import ChunkingService

        svc = EntityService()
        chunker = ChunkingService()

        entities = svc.extract_entities(SAMPLE_BOLETIN_TEXT)
        entity_map = svc.build_entity_map(entities, SAMPLE_BOLETIN_TEXT)

        chunks = chunker.chunk(SAMPLE_BOLETIN_TEXT, entity_map=entity_map)
        assert len(chunks) > 0, "Should produce at least one chunk"
        # Each chunk should have entity_anchors attribute
        for chunk in chunks:
            assert hasattr(chunk, "entity_anchors"), "ChunkResult must have entity_anchors"

    def test_chunk_enricher_uses_anchored_entities(self):
        from app.services.entity_service import EntityService
        from app.services.chunking_service import ChunkingService
        from app.services.chunk_enricher import ChunkEnricher

        svc = EntityService()
        chunker = ChunkingService()
        enricher = ChunkEnricher()

        entities = svc.extract_entities(SAMPLE_BOLETIN_TEXT)
        entity_map = svc.build_entity_map(entities, SAMPLE_BOLETIN_TEXT)
        chunks = chunker.chunk(SAMPLE_BOLETIN_TEXT, entity_map=entity_map)

        chunk = chunks[0]
        anchors = chunk.entity_anchors or []
        metadata = enricher.enrich(chunk.text, 0, "doc_test",
                                   context={"boletin_id": 1},
                                   anchored_entities=anchors if anchors else None)

        assert "entity_anchored" in metadata, "enrich() must return entity_anchored flag"
        if anchors:
            assert metadata["entity_anchored"] is True


# ── unit-level: Fase II (AIU Decomposition) ──────────────────────────────────

class TestAIUDecomposition:
    def test_decompose_acto_creates_aius(self):
        from app.services.aiu_service import AIUService, ClaimType

        svc = AIUService()
        aius = svc.decompose_acto(SAMPLE_ACTO)

        assert len(aius) >= 12, "Should generate at least 12 AIUs from a full acto with all new fields"

        types = {a.claim_type for a in aius}
        assert ClaimType.SUBJECT in types
        assert ClaimType.REFERENCE in types
        assert ClaimType.AMOUNT in types
        assert ClaimType.ACTION in types
        assert ClaimType.EVIDENCE_ANCHOR in types
        assert ClaimType.TEMPORAL in types
        assert ClaimType.RELATIONSHIP in types

    def test_decompose_actos_counts_by_type(self):
        from app.services.aiu_service import AIUService

        svc = AIUService()
        result = svc.decompose_actos([SAMPLE_ACTO])

        assert result.total_aius > 0
        assert result.source_type == "structured_acto"
        assert isinstance(result.by_type, dict)
        assert result.total_aius == len(result.aius)

    def test_all_aius_start_pending(self):
        from app.services.aiu_service import AIUService, VerificationStatus

        svc = AIUService()
        aius = svc.decompose_acto(SAMPLE_ACTO)
        for aiu in aius:
            assert aiu.verification_status == VerificationStatus.PENDING


# ── unit-level: Fase IV (Reference Firewall) ─────────────────────────────────

class TestReferenceFirewall:
    @pytest.mark.anyio
    async def test_extract_references_finds_decreto(self):
        from app.services.reference_firewall import ReferenceFirewallService

        mock_db = AsyncMock()
        mock_fts = MagicMock()
        mock_fts.search_bm25 = AsyncMock(return_value=[])

        fw = ReferenceFirewallService(db=mock_db, fts_service=mock_fts)
        refs = fw._extract_references(SAMPLE_BOLETIN_TEXT)

        ref_types = {r.ref_type for r in refs}
        assert "decreto" in ref_types or "resolucion" in ref_types, \
            f"Should find decree/resolution refs in text, got types: {ref_types}"

    @pytest.mark.anyio
    async def test_validate_references_non_blocking(self):
        """Firewall never raises — always returns a result."""
        from app.services.reference_firewall import ReferenceFirewallService

        mock_db = AsyncMock()
        # Simulate DB raising an error
        mock_db.execute = AsyncMock(side_effect=Exception("DB down"))
        mock_fts = MagicMock()
        mock_fts.search_bm25 = AsyncMock(return_value=[])

        fw = ReferenceFirewallService(db=mock_db, fts_service=mock_fts)
        result = await fw.validate_references(SAMPLE_BOLETIN_TEXT)

        # Must always return a valid result, never propagate
        assert result is not None
        assert hasattr(result, "firewall_score")
        assert 0.0 <= result.firewall_score <= 1.0

    @pytest.mark.anyio
    async def test_score_is_1_when_no_refs(self):
        from app.services.reference_firewall import ReferenceFirewallService

        mock_db = AsyncMock()
        mock_fts = MagicMock()
        mock_fts.search_bm25 = AsyncMock(return_value=[])

        fw = ReferenceFirewallService(db=mock_db, fts_service=mock_fts)
        result = await fw.validate_references("Texto sin ninguna referencia normativa.")

        assert result.firewall_score == 1.0


# ── integration: Fase III (VerificationAgent) — VCP > 0.85 ───────────────────

class TestVerificationAgent:
    def _make_retrieval_mock(self, score: float = 0.9):
        """Mock RetrievalService that always returns a high-score match."""
        mock = MagicMock()
        result = _make_mock_search_result(SAMPLE_BOLETIN_TEXT[:300], score=score)

        # hybrid_search is async
        mock.hybrid_search = AsyncMock(return_value=[result])
        # keyword_search is sync
        mock.keyword_search = MagicMock(return_value=[result])
        return mock

    @pytest.mark.anyio
    async def test_vcp_above_threshold_with_matching_corpus(self):
        """
        Core assertion: VCP > 0.85 when corpus contains the boletín data.
        Mock retrieval returns score=0.9 (VERIFIED threshold=0.7).
        """
        from app.services.aiu_service import AIUService
        from agents.verification.agent import VerificationAgent

        aiu_svc = AIUService()
        aius = aiu_svc.decompose_acto(SAMPLE_ACTO)

        retrieval = self._make_retrieval_mock(score=0.9)
        agent = VerificationAgent(retrieval_service=retrieval)

        result = await agent.verify_aius(aius, boletin_id=1)

        assert result.total_aius == len(aius)
        assert result.vcp_score > 0.85, (
            f"VCP must be > 0.85 for corpus-matched data. "
            f"Got {result.vcp_score} ({result.verified}/{result.total_aius} verified)"
        )

    @pytest.mark.anyio
    async def test_vcp_below_threshold_triggers_human_review(self):
        """Low retrieval scores → VCP < 0.85 → requires_human_review=True."""
        from app.services.aiu_service import AIUService
        from agents.verification.agent import VerificationAgent

        aiu_svc = AIUService()
        aius = aiu_svc.decompose_acto(SAMPLE_ACTO)

        retrieval = self._make_retrieval_mock(score=0.1)  # Below UNVERIFIABLE_THRESHOLD
        agent = VerificationAgent(retrieval_service=retrieval)

        result = await agent.verify_aius(aius, boletin_id=1)
        assert result.requires_human_review is True

    @pytest.mark.anyio
    async def test_empty_aius_returns_perfect_vcp(self):
        from agents.verification.agent import VerificationAgent

        agent = VerificationAgent()
        result = await agent.verify_aius([])

        assert result.vcp_score == 1.0
        assert result.total_aius == 0
        assert result.requires_human_review is False

    @pytest.mark.anyio
    async def test_verification_is_non_blocking_on_retrieval_error(self):
        """Agent handles retrieval failures gracefully — no exception propagates."""
        from app.services.aiu_service import AIUService
        from agents.verification.agent import VerificationAgent

        aiu_svc = AIUService()
        aius = aiu_svc.decompose_acto(SAMPLE_ACTO)

        bad_retrieval = MagicMock()
        bad_retrieval.hybrid_search = AsyncMock(side_effect=Exception("Network error"))
        bad_retrieval.keyword_search = MagicMock(side_effect=Exception("Network error"))

        agent = VerificationAgent(retrieval_service=bad_retrieval)
        result = await agent.verify_aius(aius, boletin_id=1)

        # Must not raise — returns result with degraded VCP
        assert result is not None
        assert result.total_aius == len(aius)


# ── integration: Fase V (VCP Metrics) ────────────────────────────────────────

class TestVCPMetrics:
    def test_record_vcp_result_updates_gauges(self):
        from app.core.observability import observability

        observability.metrics.record_vcp_result(
            vcp_score=0.92,
            total_aius=10,
            verified=9,
            unverifiable=1,
            contradicted=0,
            boletin_id=42,
            latency_ms=150.0,
        )

        gauges = observability.metrics.gauges
        assert "vcp.score" in gauges, "vcp.score gauge must be set"
        assert gauges["vcp.score"] == 0.92
        assert "vcp.score.boletin_42" in gauges

    def test_record_vcp_result_increments_counters(self):
        from app.core.observability import observability, MetricsCollector

        # Fresh collector to isolate counter state
        fresh = MetricsCollector()
        fresh.record_vcp_result(
            vcp_score=0.8,
            total_aius=5,
            verified=4,
            unverifiable=1,
            contradicted=0,
        )

        assert fresh.counters.get("vcp.aius_total", 0) == 5
        assert fresh.counters.get("vcp.aius_verified", 0) == 4
        assert fresh.counters.get("vcp.aius_unverifiable", 0) == 1
        assert fresh.counters.get("vcp.aius_contradicted", 0) == 0

    def test_module_level_record_vcp_never_raises(self):
        from app.core.observability import record_vcp

        # Should never raise, even with extreme values
        record_vcp(0.0, 0, 0, 0, 0)
        record_vcp(1.0, 100, 100, 0, 0, boletin_id=99, latency_ms=999.9)


# ── E2E: pipeline completo (sin DB, sin Gemini) ───────────────────────────────

class TestFullPipelineE2E:
    """
    Pipeline: entity_anchoring → chunking → aiu_decomposition → verification → vcp
    Sin llamadas reales a Gemini ni DB. Mock del retrieval service.
    """

    @pytest.mark.anyio
    @pytest.mark.e2e
    async def test_five_boletines_pipeline_vcp_above_085(self):
        """
        Simula el procesamiento de los 5 boletines del 02/01/2026.
        Usa SAMPLE_BOLETIN_TEXT como stand-in para cada boletín.
        Objetivo: VCP agregado > 0.85
        """
        from app.services.entity_service import EntityService
        from app.services.chunking_service import ChunkingService
        from app.services.chunk_enricher import ChunkEnricher
        from app.services.aiu_service import AIUService
        from agents.verification.agent import VerificationAgent

        entity_svc = EntityService()
        chunker = ChunkingService()
        enricher = ChunkEnricher()
        aiu_svc = AIUService()

        # Mock retrieval: score 0.9 → VERIFIED for all
        retrieval = MagicMock()
        hit = _make_mock_search_result(SAMPLE_BOLETIN_TEXT[:300], score=0.9)
        retrieval.hybrid_search = AsyncMock(return_value=[hit])
        retrieval.keyword_search = MagicMock(return_value=[hit])

        agent = VerificationAgent(retrieval_service=retrieval)

        total_vcp_scores = []
        total_aiu_count = 0
        total_verified = 0

        # Simulate 5 boletines (same text, different boletin_id)
        for boletin_id in range(1, 6):
            # Fase I: Entity anchoring
            entities = entity_svc.extract_entities(SAMPLE_BOLETIN_TEXT)
            entity_map = entity_svc.build_entity_map(entities, SAMPLE_BOLETIN_TEXT)

            # Chunking with entity map
            chunks = chunker.chunk(SAMPLE_BOLETIN_TEXT, entity_map=entity_map)
            assert len(chunks) > 0

            # Enrich chunks
            for i, chunk in enumerate(chunks):
                anchors = chunk.entity_anchors or []
                enricher.enrich(chunk.text, i, f"doc_{boletin_id}",
                                anchored_entities=anchors if anchors else None)

            # Fase II: AIU decomposition from a sample acto
            acto = {**SAMPLE_ACTO, "numero": f"2026/RSIHG-{boletin_id:08d}"}
            aius = aiu_svc.decompose_acto(acto)
            assert len(aius) > 0

            # Fase III: Verification
            result = await agent.verify_aius(aius, boletin_id=boletin_id)
            total_vcp_scores.append(result.vcp_score)
            total_aiu_count += result.total_aius
            total_verified += result.verified

            # Per-boletin assertion
            assert result.vcp_score > 0.85, (
                f"Boletin {boletin_id}: VCP={result.vcp_score:.3f} "
                f"({result.verified}/{result.total_aius}) — debe ser > 0.85"
            )

        # Global VCP assertion
        global_vcp = total_verified / total_aiu_count if total_aiu_count > 0 else 0.0
        assert global_vcp > 0.85, (
            f"VCP global={global_vcp:.3f} ({total_verified}/{total_aiu_count}) — debe ser > 0.85"
        )

        # Fase V: Record metrics
        from app.core.observability import record_vcp
        record_vcp(
            vcp_score=global_vcp,
            total_aius=total_aiu_count,
            verified=total_verified,
            unverifiable=total_aiu_count - total_verified,
            contradicted=0,
        )

    @pytest.mark.anyio
    @pytest.mark.e2e
    async def test_orchestrator_has_verification_handler(self):
        """Verificar que el OrchestatorAgent registró el VerificationAgent."""
        from agents.orchestrator.state import AgentType
        from agents.orchestrator.agent import AgentOrchestrator

        assert hasattr(AgentType, "VERIFICATION"), "AgentType debe tener VERIFICATION"
        assert AgentType.VERIFICATION == "verification"

        orchestrator = AgentOrchestrator()
        assert AgentType.VERIFICATION in orchestrator.agent_handlers, (
            "OrchestatorAgent debe tener handler registrado para VERIFICATION"
        )
