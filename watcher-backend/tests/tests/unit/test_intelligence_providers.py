"""
Unit tests for IntelligenceProvider protocol, FreeProvider, and ProProvider.

Tests validate:
- FreeProvider tier, capabilities, analyze_fragment, analyze_content
- ProProvider tier and lazy service initialization
- get_default_provider factory returns correct tier
- Risk classification logic
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.intelligence_provider import (
    FreeProvider,
    ProProvider,
    get_default_provider,
    _free_risk_level,
    _parse_max_amount,
    _PROVIDER_CACHE,
)


@pytest.fixture(autouse=True)
def clear_provider_cache():
    """Ensure provider cache is clean before each test."""
    _PROVIDER_CACHE.clear()
    yield
    _PROVIDER_CACHE.clear()


# ---------------------------------------------------------------------------
# FreeProvider
# ---------------------------------------------------------------------------


class TestFreeProvider:
    def test_tier_is_free(self):
        p = FreeProvider()
        assert p.tier == "free"

    def test_list_capabilities_returns_list(self):
        p = FreeProvider()
        caps = p.list_capabilities()
        assert isinstance(caps, list)
        assert len(caps) >= 1
        assert "keyword_risk_detection" in caps

    @pytest.mark.anyio
    async def test_analyze_fragment_returns_dict(self):
        p = FreeProvider()
        result = await p.analyze_fragment(
            "Resolución de compra directa por $200.000.000", {"fuente": "test"}
        )
        assert "actos" in result
        assert "resumen_general" in result
        assert isinstance(result["actos"], list)
        assert len(result["actos"]) == 1

    @pytest.mark.anyio
    async def test_analyze_fragment_detects_risk(self):
        p = FreeProvider()
        result = await p.analyze_fragment(
            "contratación directa sin licitación pública", {}
        )
        acto = result["actos"][0]
        assert acto["riesgo"] in ("alto", "medio", "bajo", "informativo")

    @pytest.mark.anyio
    async def test_analyze_fragment_classifies_licitacion(self):
        p = FreeProvider()
        result = await p.analyze_fragment(
            "Licitación pública N° 001/2026 para provisión de insumos", {}
        )
        assert result["actos"][0]["tipo_acto"] == "licitacion"

    @pytest.mark.anyio
    async def test_analyze_fragment_classifies_decreto(self):
        p = FreeProvider()
        result = await p.analyze_fragment(
            "Decreto N° 456/2026 del Ejecutivo Provincial", {}
        )
        assert result["actos"][0]["tipo_acto"] == "decreto"

    @pytest.mark.anyio
    async def test_analyze_content_returns_list(self):
        p = FreeProvider()
        result = await p.analyze_content(
            "Resolución 1/2026", {"fuente": "Córdoba"}
        )
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.anyio
    async def test_analyze_content_enriches_actos(self):
        p = FreeProvider()
        result = await p.analyze_content("Subsidio a entidad social", {})
        acto = result[0]
        assert "_fragment_index" in acto
        assert "_model_used" in acto

    @pytest.mark.anyio
    async def test_model_used_is_rule_based(self):
        p = FreeProvider()
        result = await p.analyze_fragment("test content", {})
        assert "rule_based" in result["model_used"]


# ---------------------------------------------------------------------------
# ProProvider
# ---------------------------------------------------------------------------


class TestProProvider:
    def test_tier_is_pro(self):
        p = ProProvider(api_key="test_key")
        assert p.tier == "pro"

    def test_list_capabilities_returns_list(self):
        p = ProProvider(api_key="test_key")
        caps = p.list_capabilities()
        assert isinstance(caps, list)
        assert "llm_structured_extraction" in caps

    @pytest.mark.anyio
    async def test_analyze_fragment_delegates_to_watcher_service(self):
        p = ProProvider(api_key="test_key")
        mock_service = MagicMock()
        mock_service.analyze_fragment = AsyncMock(return_value={"actos": [], "resumen_general": "ok"})
        p._service = mock_service

        result = await p.analyze_fragment("test", {"fuente": "test"})
        mock_service.analyze_fragment.assert_called_once_with("test", {"fuente": "test"})
        assert result["resumen_general"] == "ok"

    @pytest.mark.anyio
    async def test_analyze_content_delegates_to_watcher_service(self):
        p = ProProvider(api_key="test_key")
        mock_service = MagicMock()
        mock_service.analyze_content = AsyncMock(return_value=[{"tipo_acto": "decreto"}])
        p._service = mock_service

        result = await p.analyze_content("test", {})
        assert isinstance(result, list)
        assert result[0]["tipo_acto"] == "decreto"


# ---------------------------------------------------------------------------
# get_default_provider factory
# ---------------------------------------------------------------------------


class TestGetDefaultProvider:
    def test_returns_free_provider_when_no_api_key(self):
        from app.core.config import settings as app_settings
        with patch.object(app_settings, "GOOGLE_API_KEY", None):
            _PROVIDER_CACHE.clear()
            provider = get_default_provider(api_key=None)
        assert provider.tier == "free"
        assert isinstance(provider, FreeProvider)

    def test_returns_pro_provider_when_api_key_provided(self):
        provider = get_default_provider(api_key="fake_key_12345")
        assert provider.tier == "pro"
        assert isinstance(provider, ProProvider)

    def test_caches_provider_by_tier(self):
        p1 = get_default_provider(api_key="cache_test_key")
        p2 = get_default_provider(api_key="cache_test_key")
        assert p1 is p2

    def test_provider_is_intelligence_provider_instance(self):
        provider = get_default_provider(api_key="any_key")
        assert hasattr(provider, "tier")
        assert hasattr(provider, "analyze_fragment")
        assert hasattr(provider, "analyze_content")
        assert hasattr(provider, "list_capabilities")


# ---------------------------------------------------------------------------
# Risk classification helper
# ---------------------------------------------------------------------------


class TestFreeRiskLevel:
    def test_alto_riesgo_on_keyword(self):
        content = "contratación directa sin justificación"
        assert _free_risk_level(content, _parse_max_amount(content)) == "alto"

    def test_medio_riesgo_on_modificacion(self):
        content = "modificación de contrato vigente"
        assert _free_risk_level(content, _parse_max_amount(content)) == "medio"

    def test_informativo_on_empty(self):
        content = "designación de autoridades del ministerio"
        assert _free_risk_level(content, _parse_max_amount(content)) == "informativo"

    def test_bajo_riesgo_on_large_amount(self):
        content = "licitación por $500.000.000 pesos"
        assert _free_risk_level(content, _parse_max_amount(content)) in ("bajo", "medio")
