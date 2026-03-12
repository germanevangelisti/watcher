"""
Unit tests for CUITMaskingMiddleware.

Tests validate:
- CUIT regex matches correctly formatted and unformatted CUITs
- mask_cuit() replaces all variants
- mask_value() recurses through dicts and lists
- CUITs in text are not over-masked (non-CUIT numbers untouched)
"""

from __future__ import annotations

import pytest

from app.middleware.masking import CUIT_RE, CUIT_MASK, mask_cuit, mask_value


class TestCUITRegex:
    def test_matches_hyphenated_cuit(self):
        assert CUIT_RE.search("20-12345678-9") is not None

    def test_matches_unhyphenated_cuit(self):
        assert CUIT_RE.search("20123456789") is not None

    def test_matches_partially_hyphenated(self):
        assert CUIT_RE.search("20-123456789") is not None

    def test_does_not_match_short_number(self):
        assert CUIT_RE.search("12345") is None

    def test_does_not_match_12_digit_number(self):
        # 12 digits is not a valid CUIT (needs exactly 11)
        assert CUIT_RE.search("123456789012") is None

    def test_matches_cuit_within_text(self):
        text = "El contribuyente 20-12345678-9 presentó declaración"
        assert CUIT_RE.search(text) is not None


class TestMaskCuit:
    def test_replaces_hyphenated_cuit(self):
        result = mask_cuit("CUIT: 20-12345678-9 del contribuyente")
        assert "20-12345678-9" not in result
        assert CUIT_MASK in result

    def test_replaces_unhyphenated_cuit(self):
        result = mask_cuit("id=20123456789")
        assert "20123456789" not in result
        assert CUIT_MASK in result

    def test_replaces_multiple_cuits(self):
        text = "CUITs: 20-12345678-9 y 27-87654321-3"
        result = mask_cuit(text)
        assert result.count(CUIT_MASK) == 2

    def test_does_not_alter_non_cuit_text(self):
        text = "Resolución N° 1234 del 15/01/2026"
        assert mask_cuit(text) == text

    def test_empty_string_returns_empty(self):
        assert mask_cuit("") == ""


class TestMaskValue:
    def test_masks_string(self):
        result = mask_value("CUIT 20-12345678-9")
        assert CUIT_MASK in result

    def test_recurses_into_dict(self):
        data = {"cuit": "20-12345678-9", "nombre": "Juan"}
        result = mask_value(data)
        assert CUIT_MASK in result["cuit"]
        assert result["nombre"] == "Juan"

    def test_recurses_into_list(self):
        data = ["20-12345678-9", "texto sin CUIT"]
        result = mask_value(data)
        assert CUIT_MASK in result[0]
        assert result[1] == "texto sin CUIT"

    def test_nested_dict_in_list(self):
        data = [{"cuit": "20-12345678-9", "valor": 100}]
        result = mask_value(data)
        assert CUIT_MASK in result[0]["cuit"]
        assert result[0]["valor"] == 100

    def test_non_string_non_container_passthrough(self):
        assert mask_value(42) == 42
        assert mask_value(3.14) == 3.14
        assert mask_value(None) is None
        assert mask_value(True) is True

    def test_deeply_nested(self):
        data = {"level1": {"level2": {"cuit": "27-87654321-3"}}}
        result = mask_value(data)
        assert CUIT_MASK in result["level1"]["level2"]["cuit"]
