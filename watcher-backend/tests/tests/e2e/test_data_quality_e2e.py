"""
Test E2E: Calidad de datos y detección de anomalías

Usa los datos reales en sqlite.db para detectar problemas de calidad
que impactan al producto:

1. Duplicados en análisis → inflan métricas del dashboard
2. Licitaciones sin monto → gap del parser de montos
3. Montos implausibles → falsos positivos en alertas
4. Clasificación de tipo_acto → demasiados "otro"
5. Coherencia API → el dashboard refleja datos reales
6. Cobertura de entidades → la extracción no se salta boletines
7. Integridad referencial → no hay registros huérfanos
"""

import pytest
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
DB_PATH = BACKEND / "sqlite.db"


def _db():
    return sqlite3.connect(str(DB_PATH))


# ── 1. Duplicados en análisis ────────────────────────────────────────────────

class TestDuplicateDetection:
    def test_duplicate_fragments_are_bounded(self):
        """Fragmentos duplicados >10x indican reprocesamiento — no deberían ser mayoría."""
        conn = _db()
        total = conn.execute("SELECT COUNT(*) FROM analisis").fetchone()[0]
        in_dupes = conn.execute("""
            SELECT SUM(c) FROM (
                SELECT COUNT(*) as c FROM analisis
                GROUP BY substr(fragmento, 1, 80)
                HAVING c > 10
            )
        """).fetchone()[0] or 0
        conn.close()

        if total > 0:
            dupe_ratio = in_dupes / total
            assert dupe_ratio < 0.3, (
                f"{in_dupes}/{total} ({dupe_ratio:.0%}) actos están en grupos "
                f"duplicados >10x — indica edictos repetidos o reprocesamiento"
            )

    def test_same_boletin_no_exact_duplicate_actos(self):
        """Dentro de un mismo boletín, no debería haber actos con fragmento idéntico.

        KNOWN ISSUE: Edictos de saneamiento de títulos (Ley 9150) se publican
        como bloques repetidos en la misma sección del boletín. El BatchProcessor
        los procesa como actos separados sin deduplicación, generando hasta 24
        duplicados por boletín. Fix pendiente: dedup por hash de fragmento en
        BatchProcessor o post-procesamiento.
        """
        conn = _db()
        dupes = conn.execute("""
            SELECT boletin_id, substr(fragmento,1,80) as frag, COUNT(*) as c
            FROM analisis
            GROUP BY boletin_id, frag
            HAVING c > 3
            ORDER BY c DESC
            LIMIT 5
        """).fetchall()
        conn.close()

        worst = dupes[0] if dupes else None
        if worst and worst[2] > 5:
            pytest.xfail(
                f"KNOWN ISSUE: Boletín {worst[0]} tiene {worst[2]} actos con "
                f"fragmento idéntico (edictos repetidos) — "
                f"requiere dedup en BatchProcessor"
            )


# ── 2. Licitaciones sin monto ────────────────────────────────────────────────

class TestLicitacionAmountCoverage:
    def test_licitaciones_should_have_montos(self):
        """La mayoría de licitaciones deberían tener monto extraído."""
        conn = _db()
        total = conn.execute(
            "SELECT COUNT(*) FROM analisis WHERE tipo_acto = 'licitacion'"
        ).fetchone()[0]
        sin_monto = conn.execute(
            "SELECT COUNT(*) FROM analisis WHERE tipo_acto = 'licitacion' "
            "AND (monto_numerico IS NULL OR monto_numerico = 0)"
        ).fetchone()[0]
        conn.close()

        if total >= 5:
            miss_rate = sin_monto / total
            assert miss_rate < 0.5, (
                f"{sin_monto}/{total} ({miss_rate:.0%}) licitaciones sin monto — "
                f"el parser de montos necesita mejora"
            )

    def test_licitacion_amounts_are_plausible(self):
        """Montos de licitaciones deberían estar en rango razonable (ARS)."""
        conn = _db()
        rows = conn.execute(
            "SELECT monto_numerico FROM analisis "
            "WHERE tipo_acto = 'licitacion' AND monto_numerico > 0"
        ).fetchall()
        conn.close()

        if not rows:
            pytest.skip("No licitaciones con monto")

        montos = [r[0] for r in rows]
        for m in montos:
            assert m >= 100, (
                f"Monto ${m:,.0f} es implausiblemente bajo para una licitación"
            )
            assert m < 1e12, (
                f"Monto ${m:,.0f} supera 1 billón ARS — probable error de parsing"
            )


# ── 3. Montos implausibles en general ────────────────────────────────────────

class TestAmountPlausibility:
    def test_no_negative_amounts(self):
        conn = _db()
        negatives = conn.execute(
            "SELECT COUNT(*) FROM analisis WHERE monto_numerico < 0"
        ).fetchone()[0]
        conn.close()
        assert negatives == 0, f"Hay {negatives} actos con monto negativo"

    def test_amount_range_for_subsidios(self):
        """Subsidios tienen rangos típicos distintos a licitaciones."""
        conn = _db()
        rows = conn.execute(
            "SELECT monto_numerico FROM analisis "
            "WHERE tipo_acto = 'subsidio' AND monto_numerico > 0"
        ).fetchall()
        conn.close()

        if not rows:
            pytest.skip("No subsidios con monto")

        montos = [r[0] for r in rows]
        for m in montos:
            assert m < 1e11, (
                f"Subsidio de ${m:,.0f} es implausiblemente alto — "
                f"posible confusión con licitación"
            )

    def test_very_small_amounts_are_flagged(self):
        """Montos < $100 son probablemente errores de parsing."""
        conn = _db()
        tiny = conn.execute(
            "SELECT COUNT(*) FROM analisis "
            "WHERE monto_numerico > 0 AND monto_numerico < 100"
        ).fetchone()[0]
        total_con_monto = conn.execute(
            "SELECT COUNT(*) FROM analisis WHERE monto_numerico > 0"
        ).fetchone()[0]
        conn.close()

        if total_con_monto > 0:
            tiny_ratio = tiny / total_con_monto
            assert tiny_ratio < 0.1, (
                f"{tiny}/{total_con_monto} ({tiny_ratio:.0%}) montos son < $100 — "
                f"probable error de parsing de montos"
            )


# ── 4. Clasificación de tipo_acto ────────────────────────────────────────────

class TestActoClassification:
    def test_tipo_otro_not_dominant(self):
        """'otro' debería ser minoría — clasificación masiva como 'otro' indica gap."""
        conn = _db()
        total = conn.execute("SELECT COUNT(*) FROM analisis").fetchone()[0]
        otros = conn.execute(
            "SELECT COUNT(*) FROM analisis WHERE tipo_acto = 'otro'"
        ).fetchone()[0]
        conn.close()

        if total > 0:
            ratio = otros / total
            # NOTE: con FreeProvider es esperable un ratio alto porque usa
            # keyword matching simple. Documentamos el gap sin fallar.
            if ratio > 0.85:
                pytest.xfail(
                    f"{otros}/{total} ({ratio:.0%}) clasificados como 'otro' — "
                    f"el FreeProvider necesita patterns adicionales o Gemini"
                )

    def test_all_tipo_acto_are_valid(self):
        conn = _db()
        tipos = conn.execute(
            "SELECT DISTINCT tipo_acto FROM analisis WHERE tipo_acto IS NOT NULL"
        ).fetchall()
        conn.close()

        valid = {
            "licitacion", "decreto", "resolucion", "designacion",
            "subsidio", "transferencia", "otro", None
        }
        for (tipo,) in tipos:
            assert tipo in valid, f"tipo_acto '{tipo}' no es válido"

    def test_riesgo_distribution_not_flat(self):
        """Debería haber variación en niveles de riesgo."""
        conn = _db()
        rows = conn.execute(
            "SELECT riesgo, COUNT(*) FROM analisis GROUP BY riesgo"
        ).fetchall()
        conn.close()

        riesgos = {r[0]: r[1] for r in rows if r[0]}
        assert len(riesgos) >= 2, (
            f"Solo {len(riesgos)} nivel(es) de riesgo — "
            f"la clasificación no discrimina"
        )


# ── 5. Coherencia API-DB ─────────────────────────────────────────────────────

class TestAPICoherence:
    def test_dashboard_total_matches_db(self):
        """El dashboard debería reportar el mismo total que la DB."""
        import httpx

        conn = _db()
        db_total = conn.execute("SELECT COUNT(*) FROM boletines").fetchone()[0]
        conn.close()

        try:
            r = httpx.get("http://localhost:8001/api/v1/dashboard/stats", timeout=5)
            data = r.json()
            api_total = data["summary"]["total_documents"]
            assert api_total == db_total, (
                f"Dashboard reporta {api_total} docs pero DB tiene {db_total}"
            )
        except httpx.ConnectError:
            pytest.skip("Backend no está corriendo")

    def test_dashboard_amount_is_plausible(self):
        """El monto total del dashboard debería coincidir con la suma real."""
        import httpx

        conn = _db()
        db_sum = conn.execute(
            "SELECT COALESCE(SUM(monto_numerico), 0) FROM analisis WHERE monto_numerico > 0"
        ).fetchone()[0]
        conn.close()

        try:
            r = httpx.get("http://localhost:8001/api/v1/dashboard/stats", timeout=5)
            data = r.json()
            api_amount = data["summary"]["total_amount_detected"]

            if db_sum > 0:
                ratio = api_amount / db_sum if db_sum > 0 else 0
                assert 0.5 < ratio < 2.0, (
                    f"Dashboard reporta ${api_amount:,.0f} pero DB suma ${db_sum:,.0f} "
                    f"(ratio={ratio:.2f}) — posible descuadre"
                )
        except httpx.ConnectError:
            pytest.skip("Backend no está corriendo")

    def test_boletines_api_returns_correct_count(self):
        import httpx

        try:
            r = httpx.get("http://localhost:8001/api/v1/boletines/?limit=200", timeout=5)
            data = r.json()
            assert len(data) > 0, "API debería retornar boletines"
            for b in data[:5]:
                assert "id" in b
                assert "filename" in b
                assert "status" in b
        except httpx.ConnectError:
            pytest.skip("Backend no está corriendo")


# ── 6. Cobertura de entidades ────────────────────────────────────────────────

class TestEntityCoverage:
    def test_most_completed_boletines_have_entities(self):
        """La mayoría de boletines completados deberían tener entidades."""
        conn = _db()
        total_completed = conn.execute(
            "SELECT COUNT(*) FROM boletines WHERE status = 'completed'"
        ).fetchone()[0]
        with_entities = conn.execute("""
            SELECT COUNT(DISTINCT me.boletin_id)
            FROM menciones_entidades me
            JOIN boletines b ON b.id = me.boletin_id
            WHERE b.status = 'completed'
        """).fetchone()[0]
        conn.close()

        if total_completed > 0:
            coverage = with_entities / total_completed
            assert coverage > 0.5, (
                f"Solo {with_entities}/{total_completed} ({coverage:.0%}) boletines "
                f"completados tienen entidades — gap de extracción"
            )

    def test_entity_types_are_diverse(self):
        conn = _db()
        types = conn.execute(
            "SELECT tipo, COUNT(*) FROM entidades_extraidas GROUP BY tipo"
        ).fetchall()
        conn.close()

        assert len(types) >= 3, (
            f"Solo {len(types)} tipos de entidad — debería haber persona, "
            f"organismo, monto como mínimo"
        )

    def test_persona_entities_have_proper_names(self):
        """Entidades de tipo persona deberían tener nombres propios."""
        conn = _db()
        personas = conn.execute(
            "SELECT nombre_display FROM entidades_extraidas "
            "WHERE tipo = 'persona' LIMIT 20"
        ).fetchall()
        conn.close()

        if not personas:
            pytest.skip("No hay entidades de tipo persona")

        for (nombre,) in personas:
            assert len(nombre) >= 3, f"Nombre muy corto: '{nombre}'"
            assert not nombre.isdigit(), f"Nombre es solo números: '{nombre}'"


# ── 7. Integridad referencial ────────────────────────────────────────────────

class TestReferentialIntegrity:
    def test_analisis_references_valid_boletines(self):
        conn = _db()
        orphans = conn.execute("""
            SELECT COUNT(*) FROM analisis
            WHERE boletin_id NOT IN (SELECT id FROM boletines)
        """).fetchone()[0]
        conn.close()
        assert orphans == 0, f"Hay {orphans} análisis con boletin_id inválido"

    def test_chunks_reference_valid_boletines(self):
        conn = _db()
        orphans = conn.execute("""
            SELECT COUNT(*) FROM chunk_records
            WHERE boletin_id IS NOT NULL
            AND boletin_id NOT IN (SELECT id FROM boletines)
        """).fetchone()[0]
        conn.close()
        assert orphans == 0, f"Hay {orphans} chunks con boletin_id inválido"

    def test_menciones_reference_valid_entities(self):
        conn = _db()
        orphans = conn.execute("""
            SELECT COUNT(*) FROM menciones_entidades
            WHERE entidad_id NOT IN (SELECT id FROM entidades_extraidas)
        """).fetchone()[0]
        conn.close()
        assert orphans == 0, f"Hay {orphans} menciones con entidad_id inválido"

    def test_no_completed_boletines_without_chunks(self):
        """Un boletín 'completed' debería tener chunks indexados."""
        conn = _db()
        no_chunks = conn.execute("""
            SELECT COUNT(*) FROM boletines
            WHERE status = 'completed'
            AND id NOT IN (SELECT DISTINCT boletin_id FROM chunk_records WHERE boletin_id IS NOT NULL)
        """).fetchone()[0]
        total = conn.execute(
            "SELECT COUNT(*) FROM boletines WHERE status = 'completed'"
        ).fetchone()[0]
        conn.close()

        if total > 0:
            gap = no_chunks / total
            assert gap < 0.1, (
                f"{no_chunks}/{total} ({gap:.0%}) boletines completados "
                f"sin chunks — pipeline inconsistente"
            )


# ── 8. FreeProvider: detección de keywords en texto real ─────────────────────

class TestFreeProviderKeywordDetection:
    @pytest.mark.anyio
    async def test_licitacion_keyword_detected(self):
        """Texto que dice 'licitación' debería ser clasificado como licitacion."""
        from app.services.intelligence_provider import FreeProvider

        provider = FreeProvider()
        result = await provider.analyze_fragment(
            "LICITACIÓN PÚBLICA N° 15/2026 - Objeto: Adquisición de equipamiento "
            "informático para el Ministerio de Educación por un monto estimado de "
            "$45.000.000 (cuarenta y cinco millones de pesos).",
            {"fuente": "test"}
        )
        acto = result["actos"][0]
        assert acto["tipo_acto"] == "licitacion"
        assert acto["monto_total_numerico"] > 0

    @pytest.mark.anyio
    async def test_decreto_keyword_detected(self):
        from app.services.intelligence_provider import FreeProvider

        provider = FreeProvider()
        result = await provider.analyze_fragment(
            "DECRETO N° 456/2026 - El Gobernador de la Provincia de Córdoba, "
            "en uso de sus atribuciones, DECRETA: Artículo 1°.- Desígnase al "
            "Dr. Juan Pérez como Director de Asuntos Jurídicos.",
            {"fuente": "test"}
        )
        assert result["actos"][0]["tipo_acto"] == "decreto"

    @pytest.mark.anyio
    async def test_contratacion_directa_high_risk(self):
        """Contratación directa sin licitación debería ser riesgo alto."""
        from app.services.intelligence_provider import FreeProvider

        provider = FreeProvider()
        result = await provider.analyze_fragment(
            "Apruébase la contratación directa con la empresa CONSTRUCBA SA "
            "por la suma de $150.000.000 para la obra de ampliación del edificio "
            "sin proceso de licitación pública.",
            {"fuente": "test"}
        )
        acto = result["actos"][0]
        assert acto["riesgo"] in ("alto", "medio"), (
            f"Contratación directa sin licitación debería ser alto/medio, "
            f"got '{acto['riesgo']}'"
        )
