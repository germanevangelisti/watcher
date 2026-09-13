"""Unit tests for RerankerService strategy selection (H.1 local-first)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.reranker_service import (
    GoogleReranker,
    NoopReranker,
    RerankerService,
)


def test_noop_strategy():
    svc = RerankerService("noop")
    assert isinstance(svc.reranker, NoopReranker)


def test_unknown_strategy_is_noop():
    svc = RerankerService("not-a-real-strategy")
    assert isinstance(svc.reranker, NoopReranker)


def test_auto_local_prefers_cross_encoder():
    fake = MagicMock()
    with (
        patch("app.services.reranker_service.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("app.services.reranker_service.CrossEncoderReranker", return_value=fake),
        patch("app.core.hardware.prefer_local_ai", return_value=True),
        patch("app.core.hardware.rerank_strategy_default", return_value=None),
    ):
        svc = RerankerService(None)
    assert svc.reranker is fake


def test_auto_cloud_prefers_google_when_key_present():
    fake = MagicMock()
    with (
        patch("app.services.reranker_service.GOOGLE_AI_AVAILABLE", True),
        patch("app.services.reranker_service.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("app.services.reranker_service.GoogleReranker", return_value=fake),
        patch("app.core.hardware.prefer_local_ai", return_value=False),
        patch("app.core.hardware.rerank_strategy_default", return_value=None),
        patch.dict("os.environ", {"GOOGLE_API_KEY": "gk-test"}, clear=False),
    ):
        svc = RerankerService(None)
    assert svc.reranker is fake
    assert not isinstance(svc.reranker, NoopReranker)


def test_google_strategy_without_key_falls_back_to_noop():
    with (
        patch("app.services.reranker_service.GOOGLE_AI_AVAILABLE", True),
        patch.dict("os.environ", {"GOOGLE_API_KEY": ""}, clear=False),
    ):
        svc = RerankerService("google")
    assert isinstance(svc.reranker, NoopReranker)


def test_noop_passthrough():
    class _Hit:
        def __init__(self, text, score):
            self.chunk_id = text
            self.text = text
            self.score = score

    hits = [_Hit("a", 0.2), _Hit("b", 0.9)]
    out = NoopReranker().rerank("q", hits, top_k=1)
    assert len(out) == 1
    assert out[0].text == "a"


def test_google_reranker_class_exported():
    assert GoogleReranker is not None
