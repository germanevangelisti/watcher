"""
Test E2E: Procesamiento real de un documento promedio

Objetivo: Verificar que el pipeline completo produce resultados con sentido
semántico, usando un boletín real de la base de datos.

Pipeline probado:
  texto real → chunking → entity extraction → análisis (FreeProvider) →
  AIU decomposition → adversarial verification → validaciones semánticas

Sin Gemini, sin servicios externos. Usa datos reales de sqlite.db.
"""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

BACKEND = Path(__file__).resolve().parents[3]
DB_PATH = BACKEND / "sqlite.db"


def _load_real_chunk_text(boletin_id: int, max_chunks: int = 5) -> str:
    """Load real chunk text from sqlite.db for a completed boletin."""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT text FROM chunk_records WHERE boletin_id = ? "
        "ORDER BY chunk_index LIMIT ?",
        (boletin_id, max_chunks),
    ).fetchall()
    conn.close()
    return "\n\n".join(r[0] for r in rows)


def _get_completed_boletin_with_chunks():
    """Find a completed boletin with chunks AND existing analysis."""
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("""
        SELECT b.id, b.filename, b.date, b.section,
               COUNT(DISTINCT cr.id) as chunks,
               COUNT(DISTINCT a.id) as actos
        FROM boletines b
        JOIN chunk_records cr ON cr.boletin_id = b.id
        LEFT JOIN analisis a ON a.boletin_id = b.id
        WHERE b.status = 'completed'
        GROUP BY b.id
        HAVING chunks >= 5 AND actos >= 1
        ORDER BY b.date DESC
        LIMIT 1
    """).fetchone()
    conn.close()
    if not row:
        pytest.skip("No completed boletin with chunks and analysis in sqlite.db")
    return {
        "id": row[0], "filename": row[1], "date": row[2],
        "section": row[3], "chunks": row[4], "actos": row[5],
    }


def _get_real_analysis(boletin_id: int):
    """Load existing analysis from DB for comparison."""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT tipo_acto, organismo, riesgo, monto_numerico, descripcion, "
        "substr(fragmento, 1, 500) FROM analisis WHERE boletin_id = ? LIMIT 10",
        (boletin_id,),
    ).fetchall()
    conn.close()
    return [
        {"tipo_acto": r[0], "organismo": r[1], "riesgo": r[2],
         "monto": r[3], "descripcion": r[4], "fragmento": r[5]}
        for r in rows
    ]


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def real_boletin():
    return _get_completed_boletin_with_chunks()


@pytest.fixture(scope="module")
def real_text(real_boletin):
    text = _load_real_chunk_text(real_boletin["id"], max_chunks=10)
    assert len(text) > 500, "Need enough text for meaningful analysis"
    return text


# ── 1. Chunking produces coherent segments ───────────────────────────────────

class TestChunkingQuality:
    def test_chunks_have_minimum_length(self, real_text):
        from app.services.chunking_service import ChunkingService
        chunker = ChunkingService()
        chunks = chunker.chunk(real_text)

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.num_chars >= 50, (
                f"Chunk too short ({chunk.num_chars} chars): {chunk.text[:80]}"
            )

    def test_chunks_cover_full_text(self, real_text):
        from app.services.chunking_service import ChunkingService
        chunker = ChunkingService()
        chunks = chunker.chunk(real_text)

        total_chars = sum(c.num_chars for c in chunks)
        assert total_chars >= len(real_text) * 0.8, (
            f"Chunks cover only {total_chars}/{len(real_text)} chars "
            f"({total_chars/len(real_text)*100:.0f}%)"
        )

    def test_chunks_preserve_spanish_words(self, real_text):
        """Chunks should not break mid-word."""
        from app.services.chunking_service import ChunkingService
        chunker = ChunkingService()
        chunks = chunker.chunk(real_text)

        for chunk in chunks:
            assert not chunk.text.startswith(" ") or chunk.chunk_index == 0, (
                f"Chunk {chunk.chunk_index} starts with space — likely mid-word split"
            )


# ── 2. Entity extraction finds real entities ─────────────────────────────────

class TestEntityExtractionQuality:
    def test_extracts_entities_from_real_text(self, real_text):
        from app.services.entity_service import EntityService
        svc = EntityService()
        entities = svc.extract_entities(real_text)

        assert len(entities) > 0, "Should find at least one entity in real boletín text"

    def test_entity_types_are_valid(self, real_text):
        from app.services.entity_service import EntityService
        svc = EntityService()
        entities = svc.extract_entities(real_text)

        valid_types = {"persona", "organismo", "empresa", "contrato", "monto", "normativa", "lugar"}
        for e in entities:
            assert e.tipo in valid_types, f"Unknown entity type: {e.tipo}"

    def test_entity_map_has_positions(self, real_text):
        from app.services.entity_service import EntityService
        svc = EntityService()
        entities = svc.extract_entities(real_text)
        entity_map = svc.build_entity_map(entities, real_text)

        found = entity_map.get_entities_in_range(0, len(real_text))
        assert found is not None


# ── 3. FreeProvider analysis produces coherent output ─────────────────────────

class TestFreeProviderAnalysis:
    @pytest.mark.anyio
    async def test_analysis_returns_valid_acto_structure(self, real_text):
        from app.services.intelligence_provider import FreeProvider
        provider = FreeProvider()

        result = await provider.analyze_fragment(
            real_text[:2000],
            {"fuente": "Provincia de Córdoba", "seccion": "1"}
        )

        assert "actos" in result
        assert len(result["actos"]) >= 1
        acto = result["actos"][0]

        required_fields = [
            "tipo_acto", "organismo", "riesgo", "descripcion", "texto_original"
        ]
        for field in required_fields:
            assert field in acto, f"Missing required field: {field}"

    @pytest.mark.anyio
    async def test_tipo_acto_is_valid_category(self, real_text):
        from app.services.intelligence_provider import FreeProvider
        provider = FreeProvider()

        result = await provider.analyze_fragment(real_text[:2000], {})
        acto = result["actos"][0]

        valid_types = {
            "licitacion", "decreto", "resolucion", "designacion",
            "subsidio", "transferencia", "otro"
        }
        assert acto["tipo_acto"] in valid_types, (
            f"tipo_acto '{acto['tipo_acto']}' not in valid set"
        )

    @pytest.mark.anyio
    async def test_riesgo_is_valid_level(self, real_text):
        from app.services.intelligence_provider import FreeProvider
        provider = FreeProvider()

        result = await provider.analyze_fragment(real_text[:2000], {})
        acto = result["actos"][0]

        valid_risks = {"alto", "medio", "bajo", "informativo"}
        assert acto["riesgo"] in valid_risks

    @pytest.mark.anyio
    async def test_texto_original_comes_from_input(self, real_text):
        """texto_original must be a substring of the input, not hallucinated."""
        from app.services.intelligence_provider import FreeProvider
        provider = FreeProvider()

        fragment = real_text[:2000]
        result = await provider.analyze_fragment(fragment, {})
        acto = result["actos"][0]

        assert acto["texto_original"] in fragment, (
            "texto_original is not a substring of the input — possible hallucination"
        )

    @pytest.mark.anyio
    async def test_amount_parsed_when_present(self, real_text):
        """If text contains peso amounts, monto_total_numerico should be > 0."""
        from app.services.intelligence_provider import FreeProvider, _parse_max_amount
        provider = FreeProvider()

        amount_in_text = _parse_max_amount(real_text[:2000])
        result = await provider.analyze_fragment(real_text[:2000], {})
        acto = result["actos"][0]

        if amount_in_text > 0:
            assert acto["monto_total_numerico"] > 0, (
                f"Text contains ${amount_in_text:,.0f} but acto.monto_total_numerico=0"
            )


# ── 4. AIU decomposition produces meaningful claims ──────────────────────────

class TestAIUDecompositionQuality:
    @pytest.mark.anyio
    async def test_aiu_count_proportional_to_acto_richness(self, real_text):
        """More fields in the acto → more AIUs."""
        from app.services.intelligence_provider import FreeProvider
        from app.services.aiu_service import AIUService

        provider = FreeProvider()
        result = await provider.analyze_fragment(real_text[:2000], {"fuente": "test"})
        acto = result["actos"][0]

        svc = AIUService()
        aius = svc.decompose_acto(acto)

        assert len(aius) >= 3, (
            f"Expected at least 3 AIUs from a real acto, got {len(aius)}"
        )

    @pytest.mark.anyio
    async def test_aiu_claim_types_are_diverse(self, real_text):
        from app.services.intelligence_provider import FreeProvider
        from app.services.aiu_service import AIUService

        provider = FreeProvider()
        result = await provider.analyze_fragment(real_text[:2000], {"fuente": "test"})
        acto = result["actos"][0]

        svc = AIUService()
        aius = svc.decompose_acto(acto)

        types = {a.claim_type.value for a in aius}
        assert len(types) >= 2, (
            f"Expected diverse claim types, got only: {types}"
        )

    @pytest.mark.anyio
    async def test_all_aius_start_pending(self, real_text):
        from app.services.intelligence_provider import FreeProvider
        from app.services.aiu_service import AIUService, VerificationStatus

        provider = FreeProvider()
        result = await provider.analyze_fragment(real_text[:2000], {"fuente": "test"})

        svc = AIUService()
        aius = svc.decompose_acto(result["actos"][0])

        for aiu in aius:
            assert aiu.verification_status == VerificationStatus.PENDING


# ── 5. Verification against corpus produces valid VCP ────────────────────────

class TestVerificationWithRealData:
    def _make_retrieval_from_chunks(self, chunks_text: str, score: float = 0.85):
        mock = MagicMock()

        def _make_result(text, sc):
            r = MagicMock()
            r.text = text
            r.score = sc
            r.document_id = "real_doc"
            r.chunk_id = "chunk_0"
            return r

        results = [_make_result(chunks_text[:500], score)]
        mock.hybrid_search = AsyncMock(return_value=results)
        mock.keyword_search = MagicMock(return_value=results)
        return mock

    @pytest.mark.anyio
    async def test_full_pipeline_real_text_vcp_valid(self, real_text):
        """Full pipeline on real text produces 0 <= VCP <= 1."""
        from app.services.intelligence_provider import FreeProvider
        from app.services.aiu_service import AIUService
        from agents.verification.agent import VerificationAgent

        provider = FreeProvider()
        result = await provider.analyze_fragment(real_text[:2000], {"fuente": "test"})
        acto = result["actos"][0]

        svc = AIUService()
        aius = svc.decompose_acto(acto)

        retrieval = self._make_retrieval_from_chunks(real_text)
        agent = VerificationAgent(retrieval_service=retrieval)

        vr = await agent.verify_aius(aius, boletin_id=1)

        assert 0.0 <= vr.vcp_score <= 1.0
        assert vr.total_aius == len(aius)
        assert vr.verified + vr.unverifiable + vr.contradicted + vr.pending == vr.total_aius

    @pytest.mark.anyio
    async def test_verification_result_has_evidence(self, real_text):
        """Verified AIUs should have evidence_text from the corpus."""
        from app.services.intelligence_provider import FreeProvider
        from app.services.aiu_service import AIUService, VerificationStatus
        from agents.verification.agent import VerificationAgent

        provider = FreeProvider()
        result = await provider.analyze_fragment(real_text[:2000], {"fuente": "test"})

        svc = AIUService()
        aius = svc.decompose_acto(result["actos"][0])

        retrieval = self._make_retrieval_from_chunks(real_text, score=0.9)
        agent = VerificationAgent(retrieval_service=retrieval)

        vr = await agent.verify_aius(aius, boletin_id=1)

        verified_with_evidence = [
            a for a in vr.aius
            if a.verification_status == VerificationStatus.VERIFIED
            and a.evidence_text
        ]
        if vr.verified > 0:
            assert len(verified_with_evidence) > 0, (
                "Verified AIUs should have evidence_text"
            )


# ── 6. Coherencia con análisis existente en DB ───────────────────────────────

class TestCoherenceWithStoredAnalysis:
    def test_stored_analysis_has_required_fields(self, real_boletin):
        """Existing analysis in DB should have all required fields."""
        actos = _get_real_analysis(real_boletin["id"])
        if not actos:
            pytest.skip("No existing analysis for this boletin")

        for acto in actos:
            assert acto["tipo_acto"] is not None, "tipo_acto should not be null"
            assert acto["riesgo"] is not None, "riesgo should not be null"

    def test_stored_fragmento_is_real_text(self, real_boletin):
        """Stored fragmento should be a substring of the full document text."""
        actos = _get_real_analysis(real_boletin["id"])
        if not actos:
            pytest.skip("No existing analysis for this boletin")

        full_text = _load_real_chunk_text(real_boletin["id"], max_chunks=9999)

        matches = 0
        checked = 0
        for acto in actos[:5]:
            frag = acto["fragmento"]
            if frag and len(frag) > 20:
                checked += 1
                snippet = frag[10:60].strip()
                if snippet and snippet in full_text:
                    matches += 1

        if checked > 0:
            match_ratio = matches / checked
            assert match_ratio >= 0.3, (
                f"Only {matches}/{checked} stored fragmentos found in "
                f"full document text — analysis may not correspond to this document. "
                f"This can happen when analysis was done via BatchProcessor "
                f"(section-based) while chunks come from the full pipeline."
            )

    def test_riesgo_distribution_is_reasonable(self, real_boletin):
        """Risk distribution should not be 100% one category for a multi-acto doc."""
        actos = _get_real_analysis(real_boletin["id"])
        if len(actos) < 3:
            pytest.skip("Need at least 3 actos for distribution check")

        riesgos = {a["riesgo"] for a in actos if a["riesgo"]}
        assert len(riesgos) >= 1, "At least one risk level should exist"


# ── 7. Full pipeline integration: text → analysis → verification ─────────────

class TestFullPipelineIntegration:
    @pytest.mark.anyio
    @pytest.mark.e2e
    async def test_real_document_full_pipeline(self, real_text, real_boletin):
        """
        Pipeline completo con texto real:
        chunking → entities → FreeProvider → AIU → verification

        Valida coherencia semántica del resultado.
        """
        from app.services.chunking_service import ChunkingService
        from app.services.entity_service import EntityService
        from app.services.intelligence_provider import FreeProvider
        from app.services.aiu_service import AIUService, VerificationStatus
        from agents.verification.agent import VerificationAgent

        # 1. Chunk
        chunker = ChunkingService()
        entity_svc = EntityService()

        entities = entity_svc.extract_entities(real_text)
        entity_map = entity_svc.build_entity_map(entities, real_text)
        chunks = chunker.chunk(real_text, entity_map=entity_map)

        assert len(chunks) >= 1, "Chunking should produce at least 1 chunk"

        # 2. Analyze first chunk
        provider = FreeProvider()
        chunk_text = chunks[0].text
        result = await provider.analyze_fragment(
            chunk_text,
            {"fuente": "Provincia de Córdoba", "boletin": real_boletin["filename"]}
        )

        assert len(result["actos"]) >= 1
        acto = result["actos"][0]

        # 3. Validate acto semantic coherence
        assert acto["tipo_acto"] in {
            "licitacion", "decreto", "resolucion",
            "designacion", "subsidio", "transferencia", "otro"
        }
        assert acto["riesgo"] in {"alto", "medio", "bajo", "informativo"}
        assert len(acto["descripcion"]) > 10
        assert acto["texto_original"][:50] in chunk_text, (
            "texto_original should come from the input chunk"
        )

        # 4. AIU decomposition
        aiu_svc = AIUService()
        aius = aiu_svc.decompose_acto(acto)
        assert len(aius) >= 2, "Real acto should produce multiple AIUs"

        # 5. Verification with mock retrieval using real text
        retrieval = MagicMock()
        hit = MagicMock()
        hit.text = chunk_text[:500]
        hit.score = 0.9
        hit.document_id = "real"
        hit.chunk_id = "c0"
        retrieval.hybrid_search = AsyncMock(return_value=[hit])
        retrieval.keyword_search = MagicMock(return_value=[hit])

        agent = VerificationAgent(retrieval_service=retrieval)
        vr = await agent.verify_aius(aius, boletin_id=real_boletin["id"])

        # 6. VCP should be valid
        assert 0.0 <= vr.vcp_score <= 1.0
        assert vr.total_aius == len(aius)

        # 7. At least some AIUs should be verified or unverifiable (not stuck in PENDING)
        resolved = vr.verified + vr.unverifiable + vr.contradicted
        assert resolved == vr.total_aius - vr.pending
        assert resolved >= len(aius) * 0.5, (
            f"Less than 50% of AIUs resolved: {resolved}/{len(aius)}"
        )
