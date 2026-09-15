"""Unit tests for app.services.extraction_goldset (V.1.2)."""

from app.services.extraction_goldset import (
    ExtractedAct,
    GoldAct,
    evaluate_goldset,
    match_one,
    normalize_numero,
    relative_monto_error,
)


class TestNormalizeNumero:
    def test_s511_variants_share_stem(self):
        a = normalize_numero("S-511/2026") or ""
        b = normalize_numero("S-511") or ""
        assert "511" in a and "511" in b
        gold = GoldAct(
            filename="f.pdf", gold_id="g", numero_acto="S-511/2026",
        )
        extracted = ExtractedAct(
            analisis_id=1, filename="f.pdf", numero_acto="S-511",
        )
        assert match_one(gold, [extracted]).extracted is not None


class TestMontoError:
    def test_zero_when_equal(self):
        assert relative_monto_error(100.0, 100.0) == 0.0

    def test_two_percent(self):
        assert abs(relative_monto_error(102.0, 100.0) - 0.02) < 1e-9


class TestMatch:
    def test_matches_on_numero(self):
        gold = GoldAct(
            filename="20260303_4_Secc.pdf",
            gold_id="g1",
            numero_acto="S-511/2026",
            monto=25_341_354_988.89,
        )
        extracted = ExtractedAct(
            analisis_id=1,
            filename="20260303_4_Secc.pdf",
            numero_acto="RESOLUCION 056/2026 S-511/2026",
            monto=25_341_354_988.89,
        )
        match = match_one(gold, [extracted])
        assert match.extracted is not None
        assert match.method == "numero_acto"

    def test_rejects_numero_when_monto_is_another_pliego(self):
        gold = GoldAct(
            filename="20260202_4_Secc.pdf",
            gold_id="g-epec-1231",
            numero_acto="1231",
            organismo="EPEC",
            monto=61_068_700.14,
        )
        extracted = ExtractedAct(
            analisis_id=1,
            filename="20260202_4_Secc.pdf",
            numero_acto="1231",
            organismo="Otro ente",
            monto=1_525_000_000.0,
        )
        match = match_one(gold, [extracted])
        assert match.extracted is None
        assert match.method == "unmatched"

    def test_organismo_without_monto_does_not_match(self):
        gold = GoldAct(
            filename="20260202_3_Secc.pdf",
            gold_id="g-asamblea",
            tipo_acto="otro",
            organismo="ASOCIACION MUTUAL DE EMPLEADOS",
            is_gasto_publico=False,
        )
        extracted = ExtractedAct(
            analisis_id=2,
            filename="20260202_3_Secc.pdf",
            tipo_acto="otro",
            organismo="ASOCIACION MUTUAL DE EMPLEADOS Y FUNCIONARIOS",
            numero_acto="No 643948",
            monto=1.0,
        )
        match = match_one(gold, [extracted])
        assert match.extracted is None

    def test_skips_organismo_monto_when_numero_conflicts(self):
        gold = GoldAct(
            filename="20260227_4_Secc.pdf",
            gold_id="g-mds",
            numero_acto="2026/PRSGA-00000011",
            organismo="Ministerio de Desarrollo Social y Promoción del Empleo",
            monto=1_008_500_438.40,
        )
        extracted = ExtractedAct(
            analisis_id=3,
            filename="20260227_4_Secc.pdf",
            numero_acto="GG-021",
            organismo="Ministerio de Desarrollo Social y Promoción del Empleo",
            monto=1_008_500_438.40,
        )
        match = match_one(gold, [extracted])
        assert match.extracted is None

    def test_unmatched_when_nothing_close(self):
        gold = GoldAct(
            filename="20260303_4_Secc.pdf",
            gold_id="g1",
            numero_acto="S-511/2026",
            organismo="UNIDAD EJECUTORA",
            monto=25_341_354_988.89,
        )
        extracted = ExtractedAct(
            analisis_id=9,
            filename="20260303_4_Secc.pdf",
            numero_acto="12/2026",
            organismo="EPEC",
            monto=100.0,
        )
        assert match_one(gold, [extracted]).extracted is None

    def test_recall_and_s4_numero(self):
        gold = [
            GoldAct(
                filename="20260303_4_Secc.pdf",
                gold_id="g1",
                numero_acto="S-511/2026",
                monto=100.0,
                complete_gasto=True,
            )
        ]
        extracted = [
            ExtractedAct(
                analisis_id=1,
                filename="20260303_4_Secc.pdf",
                numero_acto="S-511/2026",
                monto=100.0,
                is_gasto_publico=True,
            )
        ]
        metrics = evaluate_goldset(gold, extracted)
        assert metrics.recall == 1.0
        assert metrics.s4_with_numero == 1
        assert metrics.precision == 1.0
