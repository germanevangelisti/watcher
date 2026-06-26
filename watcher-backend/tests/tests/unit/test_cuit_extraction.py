"""Unit tests for CUIT/CUIL extraction & normalization — Épica 3.3.

El masking de CUIT en respuestas HTTP ya está cubierto por
``test_masking_middleware.py``. Aquí validamos la **extracción** y
**normalización** que antes faltaban en EntityService.
"""

from __future__ import annotations

import pytest

from app.services.entity_service import EntityService


@pytest.fixture
def service() -> EntityService:
    return EntityService()


class TestNormalizeCuit:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("20-12345678-9", "20-12345678-9"),
            ("20123456789", "20-12345678-9"),
            ("20 12345678 9", "20-12345678-9"),
            ("CUIT 20-12345678-9", "20-12345678-9"),
        ],
    )
    def test_normalize_valid(self, raw, expected):
        assert EntityService.normalize_cuit(raw) == expected

    @pytest.mark.parametrize("raw", ["123", "", "abc", "20-1234-9", None])
    def test_normalize_invalid_returns_none(self, raw):
        assert EntityService.normalize_cuit(raw) is None


class TestCuitChecksum:
    def test_valid_cuit_checksum(self):
        # CUIT con dígito verificador correcto (módulo 11)
        assert EntityService.is_valid_cuit("20-12345678-6") is True

    def test_invalid_cuit_checksum(self):
        assert EntityService.is_valid_cuit("20-12345678-0") is False

    def test_wrong_length(self):
        assert EntityService.is_valid_cuit("123") is False


class TestExtractCuits:
    def test_extracts_formatted_cuit(self, service):
        text = "Se adjudica a TECH SRL, CUIT 20-12345678-6, la licitación."
        entities = service.extract_entities(text)
        cuits = [e for e in entities if e.tipo == "cuit"]
        assert any(e.nombre_normalizado == "20-12345678-6" for e in cuits)

    def test_extracts_unformatted_cuit_with_prefix(self, service):
        text = "El proveedor con C.U.I.T. 20123456786 fue seleccionado."
        entities = service.extract_entities(text)
        cuits = [e for e in entities if e.tipo == "cuit"]
        assert any(e.nombre_normalizado == "20-12345678-6" for e in cuits)

    def test_invalid_checksum_lower_confidence(self, service):
        text = "Beneficiario CUIT 20-12345678-0 recibe el subsidio."
        entities = service.extract_entities(text)
        cuits = [e for e in entities if e.tipo == "cuit"]
        assert cuits, "Debe extraer el CUIT aunque el dígito sea inválido"
        flagged = next(e for e in cuits if e.nombre_normalizado == "20-12345678-0")
        assert flagged.confianza < 0.95
        assert flagged.metadata["valido"] is False

    def test_dedup_same_cuit(self, service):
        text = "CUIT 20-12345678-6 ... y nuevamente 20-12345678-6 aparece."
        entities = service.extract_entities(text)
        cuits = [e for e in entities if e.tipo == "cuit"]
        norms = [e.nombre_normalizado for e in cuits]
        assert norms.count("20-12345678-6") == 1

    def test_no_false_positive_on_plain_numbers(self, service):
        text = "El expediente 1234 del año 2026 fue aprobado sin observaciones."
        entities = service.extract_entities(text)
        cuits = [e for e in entities if e.tipo == "cuit"]
        assert cuits == []
