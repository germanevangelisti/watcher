"""Unit tests for Épica 3 — Feature Engineering per acto.

Cubre:
- TransparencyScorer: rango 0–100, suma por campos, penalización por descripción.
- RedFlagClassifier: tipología canónica de irregularidades.
- ActoFeatureEngineer: fachada combinada.
- Helpers de parseo de montos y presencia de campos.
"""

from __future__ import annotations

import pytest
from app.services.feature_engineering import (
    ActoFeatureEngineer,
    RedFlagClassifier,
    RedFlagConfig,
    RedFlagType,
    Severity,
    TransparencyScorer,
    _acto_monto,
    _is_present,
    _parse_amount_string,
    get_feature_engineer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, False),
            ("", False),
            ("   ", False),
            ("No especificado", False),
            ("N/A", False),
            ([], False),
            ({}, False),
            ("Ministerio de Salud", True),
            (["beneficiario"], True),
            (42, True),
        ],
    )
    def test_is_present(self, value, expected):
        assert _is_present(value) is expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("$3.010.523.733,29", 3010523733.29),
            ("pesos 1.000.000", 1000000.0),
            ("1500", 1500.0),
            ("sin monto", 0.0),
            ("12,50", 12.5),
        ],
    )
    def test_parse_amount_string(self, raw, expected):
        assert _parse_amount_string(raw) == pytest.approx(expected)

    def test_acto_monto_prefers_numeric(self):
        acto = {"monto_total_numerico": 5000.0, "montos": ["$1.000"]}
        assert _acto_monto(acto) == 5000.0

    def test_acto_monto_fallback_to_strings(self):
        acto = {"montos": ["$1.000.000", "$500.000"]}
        assert _acto_monto(acto) == pytest.approx(1500000.0)


# ---------------------------------------------------------------------------
# TransparencyScorer
# ---------------------------------------------------------------------------


class TestTransparencyScorer:
    def test_empty_acto_scores_low(self):
        scorer = TransparencyScorer()
        score, breakdown = scorer.score({})
        # base 30 - penalización por descripción corta = 22
        assert score == pytest.approx(22.0)
        assert breakdown["base"] == 30.0
        assert breakdown["descripcion_penalty"] == -8.0

    def test_complete_acto_scores_high(self):
        scorer = TransparencyScorer()
        acto = {
            "organismo": "Ministerio de Obras Públicas",
            "beneficiarios": ["TECH SRL"],
            "montos": ["$1.000.000"],
            "expediente": "EX-2026-123",
            "referencias_normativas": ["Ley N° 2095"],
            "imputacion_presupuestaria": "Programa 14 - Inciso 4",
            "firmante": "Ing. Roberto García",
            "fecha_acto": "2026-02-15",
            "descripcion": "Adjudicación de obra de pavimentación urbana en la ciudad.",
        }
        score, _ = scorer.score(acto)
        assert score == pytest.approx(100.0)

    def test_score_within_bounds(self):
        scorer = TransparencyScorer()
        # Acto parcial
        acto = {"organismo": "X", "descripcion": "d" * 50}
        score, _ = scorer.score(acto)
        assert 0.0 <= score <= 100.0

    def test_short_description_penalized(self):
        scorer = TransparencyScorer()
        acto_long = {"organismo": "Min", "descripcion": "x" * 60}
        acto_short = {"organismo": "Min", "descripcion": "corto"}
        score_long, _ = scorer.score(acto_long)
        score_short, _ = scorer.score(acto_short)
        assert score_long > score_short

    def test_placeholder_fields_not_counted(self):
        scorer = TransparencyScorer()
        acto = {
            "organismo": "No especificado",
            "beneficiarios": [],
            "descripcion": "x" * 60,
        }
        score, breakdown = scorer.score(acto)
        assert breakdown["organismo"] == 0.0
        assert score == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# RedFlagClassifier
# ---------------------------------------------------------------------------


class TestRedFlagClassifier:
    def test_high_amount_flag(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "licitacion",
            "monto_total_numerico": 80_000_000,
            "beneficiarios": ["X SRL"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.HIGH_AMOUNT in types

    def test_missing_beneficiary_flag(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "transferencia",
            "monto_total_numerico": 1_234_567,
            "beneficiarios": [],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        flags = clf.classify(acto)
        flag = next(f for f in flags if f.type == RedFlagType.MISSING_BENEFICIARY)
        assert flag.severity == Severity.HIGH

    def test_missing_amount_for_licitacion(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "licitacion",
            "monto_total_numerico": 0,
            "beneficiarios": ["X SRL"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.MISSING_AMOUNT in types

    def test_decreto_without_amount_no_missing_amount(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "decreto",
            "monto_total_numerico": 0,
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.MISSING_AMOUNT not in types

    def test_suspicious_amount_pattern(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "subsidio",
            "monto_total_numerico": 9999,
            "beneficiarios": ["X"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.SUSPICIOUS_AMOUNT_PATTERN in types

    def test_round_amount_flag(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "subsidio",
            "monto_total_numerico": 5_000_000,
            "beneficiarios": ["X"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.ROUND_AMOUNT in types

    def test_missing_expediente_and_legal_reference(self):
        clf = RedFlagClassifier()
        acto = {"tipo_acto": "decreto", "descripcion": "x" * 60}
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.MISSING_EXPEDIENTE in types
        assert RedFlagType.MISSING_LEGAL_REFERENCE in types

    def test_over_budget_flag(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "licitacion",
            "monto_total_numerico": 120,
            "presupuesto_oficial": 100,
            "beneficiarios": ["X"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.OVER_BUDGET in types

    def test_low_transparency_flag(self):
        clf = RedFlagClassifier()
        acto = {"tipo_acto": "decreto"}
        flags = clf.classify(acto, transparency_score=10.0)
        types = {f.type for f in flags}
        assert RedFlagType.LOW_TRANSPARENCY_SCORE in types

    def test_clean_acto_minimal_flags(self):
        clf = RedFlagClassifier()
        acto = {
            "tipo_acto": "resolucion",
            "monto_total_numerico": 1_234_567,
            "beneficiarios": ["X SRL"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto, transparency_score=90.0)}
        # No debe disparar las flags graves
        assert RedFlagType.HIGH_AMOUNT not in types
        assert RedFlagType.MISSING_BENEFICIARY not in types
        assert RedFlagType.LOW_TRANSPARENCY_SCORE not in types

    def test_custom_config_threshold(self):
        clf = RedFlagClassifier(RedFlagConfig(high_amount_threshold=1000))
        acto = {
            "tipo_acto": "subsidio",
            "monto_total_numerico": 2000,
            "beneficiarios": ["X"],
            "expediente": "EX-1",
            "referencias_normativas": ["Ley 1"],
        }
        types = {f.type for f in clf.classify(acto)}
        assert RedFlagType.HIGH_AMOUNT in types


# ---------------------------------------------------------------------------
# ActoFeatureEngineer (fachada)
# ---------------------------------------------------------------------------


class TestActoFeatureEngineer:
    def test_engineer_returns_features(self):
        engineer = ActoFeatureEngineer()
        acto = {
            "tipo_acto": "licitacion",
            "monto_total_numerico": 80_000_000,
            "beneficiarios": [],
            "descripcion": "corto",
        }
        features = engineer.engineer(acto)
        assert 0.0 <= features.transparency_score <= 100.0
        assert features.num_red_flags == len(features.red_flags)
        assert features.num_red_flags > 0

    def test_low_transparency_triggers_flag_via_facade(self):
        engineer = ActoFeatureEngineer()
        acto = {"tipo_acto": "decreto"}  # casi vacío → score bajo
        features = engineer.engineer(acto)
        types = {f.type for f in features.red_flags}
        assert RedFlagType.LOW_TRANSPARENCY_SCORE in types

    def test_to_dict_serializable(self):
        engineer = ActoFeatureEngineer()
        acto = {"tipo_acto": "subsidio", "monto_total_numerico": 9999, "beneficiarios": []}
        d = engineer.engineer(acto).to_dict()
        assert set(d.keys()) == {
            "transparency_score",
            "num_red_flags",
            "red_flags",
            "score_breakdown",
        }
        assert isinstance(d["red_flags"], list)
        if d["red_flags"]:
            assert set(d["red_flags"][0].keys()) == {
                "type",
                "severity",
                "title",
                "description",
                "evidence",
                "confidence",
            }

    def test_singleton(self):
        assert get_feature_engineer() is get_feature_engineer()
