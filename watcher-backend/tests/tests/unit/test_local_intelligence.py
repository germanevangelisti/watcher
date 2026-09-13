"""Unit tests for LocalProProvider (Ollama) without a live server."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.local_intelligence import LocalProProvider, _normalize_actos


def test_tier_and_capabilities():
    p = LocalProProvider(base_url="http://127.0.0.1:9", model="test")
    assert p.tier == "local"
    assert "local_inference" in p.list_capabilities()


def test_normalize_fills_required_fields():
    result = _normalize_actos({"actos": [{}], "resumen_general": "ok"}, {"f": 1}, "m")
    acto = result["actos"][0]
    assert acto["tipo_acto"] == "otro"
    assert acto["riesgo"] == "informativo"
    assert result["model_used"] == "m"


async def test_analyze_fragment_parses_ollama_json():
    payload = {
        "message": {
            "content": '{"actos": [{"tipo_acto": "decreto", "organismo": "X", '
            '"descripcion": "d", "riesgo": "bajo", "monto_total_numerico": 1, '
            '"texto_original": "t"}], "resumen_general": "r"}'
        }
    }
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    p = LocalProProvider(base_url="http://ollama.test", model="qwen")
    with patch("app.services.local_intelligence.httpx.AsyncClient", return_value=mock_client):
        result = await p.analyze_fragment("Decreto 1", {"fuente": "test"})

    assert result["actos"][0]["tipo_acto"] == "decreto"
    assert result["model_used"] == "qwen"
    mock_client.post.assert_awaited()
    sent = mock_client.post.await_args
    assert sent.kwargs["json"]["options"]["num_ctx"] == 4096
    assert sent.kwargs["json"]["keep_alive"] == "30m"


async def test_analyze_fragment_falls_back_to_free_on_connection_error():
    p = LocalProProvider(base_url="http://127.0.0.1:9", model="qwen")
    with patch(
        "app.services.local_intelligence.httpx.AsyncClient",
        side_effect=OSError("connection refused"),
    ):
        result = await p.analyze_fragment(
            "contratación directa sin licitación", {"fuente": "test"}
        )
    assert result["actos"]
    assert "free_fallback" in result["model_used"]


def test_watcher_service_imports_without_google_sdk():
    from app.services.watcher_service import WatcherService

    assert WatcherService is not None


async def test_watcher_service_delegates_to_local_even_if_gemini_model_exists():
    fake_genai = MagicMock()
    local = MagicMock()
    local.tier = "local"
    local.analyze_fragment = AsyncMock(
        return_value={"actos": [], "resumen_general": "from-local"}
    )
    with (
        patch.dict(
            sys.modules,
            {"google": MagicMock(), "google.generativeai": fake_genai},
        ),
        patch("app.services.watcher_service.get_default_provider", return_value=local),
        patch.dict("os.environ", {"GOOGLE_API_KEY": "fake-key"}, clear=False),
    ):
        from app.services import watcher_service as ws_mod

        ws_mod.genai = fake_genai
        svc = ws_mod.WatcherService()
        svc.model = MagicMock()
        result = await svc.analyze_fragment("Decreto 1", {"fuente": "test"})

    assert result["resumen_general"] == "from-local"
    local.analyze_fragment.assert_awaited_once()
