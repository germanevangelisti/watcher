"""Unit tests for local hardware profile and pipeline concurrency knobs."""

from __future__ import annotations

from unittest.mock import patch

from app.core.concurrency import map_bounded
from app.core.hardware import (
    default_worker_count,
    document_pipeline_concurrency,
    embedding_provider_default,
    hardware_profile,
    intelligence_provider_choice,
    llm_max_concurrent,
    ollama_num_ctx,
    pipeline_workers,
    prefer_local_ai,
    rerank_strategy_default,
)


class TestHardwareProfile:
    def test_explicit_local(self, monkeypatch):
        monkeypatch.setenv("HARDWARE_PROFILE", "local")
        assert hardware_profile() == "local"
        assert prefer_local_ai() is True

    def test_explicit_cloud(self, monkeypatch):
        monkeypatch.setenv("HARDWARE_PROFILE", "cloud")
        assert hardware_profile() == "cloud"
        assert prefer_local_ai() is False

    def test_production_defaults_to_cloud(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("HARDWARE_PROFILE", raising=False)
        assert hardware_profile() == "cloud"

    def test_development_defaults_to_local(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("HARDWARE_PROFILE", raising=False)
        assert hardware_profile() == "local"


class TestWorkers:
    def test_nproc_minus_reserve(self):
        with (
            patch("app.core.hardware.cpu_count", return_value=16),
            patch.dict("os.environ", {"PIPELINE_CPU_RESERVE": "2"}, clear=False),
        ):
            assert default_worker_count() == 14

    def test_never_below_one(self):
        with (
            patch("app.core.hardware.cpu_count", return_value=1),
            patch.dict("os.environ", {"PIPELINE_CPU_RESERVE": "8"}, clear=False),
        ):
            assert default_worker_count() == 1

    def test_explicit_pipeline_workers(self):
        with patch.dict("os.environ", {"PIPELINE_WORKERS": "6"}, clear=False):
            assert pipeline_workers() == 6

    def test_llm_concurrent_local_default_is_one(self):
        with (
            patch("app.core.hardware.prefer_local_ai", return_value=True),
            patch.dict("os.environ", {"LLM_MAX_CONCURRENT": ""}, clear=False),
        ):
            assert llm_max_concurrent() == 1

    def test_document_pipeline_follows_workers(self):
        with (
            patch("app.core.hardware.pipeline_workers", return_value=20),
            patch("app.core.hardware.llm_max_concurrent", return_value=2),
        ):
            assert document_pipeline_concurrency() == 20

    def test_ollama_ctx_default_fits_12gb(self):
        with patch.dict("os.environ", {"OLLAMA_NUM_CTX": ""}, clear=False):
            assert ollama_num_ctx() == 4096


class TestProviderDefaults:
    def test_local_profile_embeddings(self):
        with (
            patch("app.core.hardware.prefer_local_ai", return_value=True),
            patch.dict("os.environ", {"EMBEDDING_PROVIDER": ""}, clear=False),
        ):
            assert embedding_provider_default() == "local"

    def test_cloud_profile_embeddings(self):
        with (
            patch("app.core.hardware.prefer_local_ai", return_value=False),
            patch.dict("os.environ", {"EMBEDDING_PROVIDER": ""}, clear=False),
        ):
            assert embedding_provider_default() == "google"

    def test_rerank_explicit(self):
        with patch.dict("os.environ", {"RERANK_STRATEGY": "google"}, clear=False):
            assert rerank_strategy_default() == "google"

    def test_intelligence_choice(self):
        with patch.dict("os.environ", {"INTELLIGENCE_PROVIDER": "local"}, clear=False):
            assert intelligence_provider_choice() == "local"


class TestMapBounded:
    async def test_empty(self):
        assert await map_bounded([], lambda x: x, 4) == []

    async def test_respects_limit_and_collects(self):
        seen = []

        async def add(n: int) -> int:
            seen.append(n)
            return n * 2

        result = await map_bounded([1, 2, 3], add, 2, return_exceptions=False)
        assert result == [2, 4, 6]
        assert set(seen) == {1, 2, 3}

    async def test_captures_exceptions(self):
        async def boom(n: int) -> int:
            if n == 2:
                raise ValueError("nope")
            return n

        result = await map_bounded([1, 2, 3], boom, 3, return_exceptions=True)
        assert result[0] == 1
        assert isinstance(result[1], ValueError)
        assert result[2] == 3
