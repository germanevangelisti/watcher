"""
Unit tests for BoletinPipeline ABC contract.

Tests the base class behaviour using a minimal concrete subclass
that does NOT touch the database (IngestionRun interactions are mocked).
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipelines.base import BoletinPipeline, PipelineResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> AsyncMock:
    """Return a minimal async DB session mock."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_run(run_id: int = 1) -> MagicMock:
    run = MagicMock()
    run.id = run_id
    run.started_at = datetime(2026, 3, 10, 12, 0, 0)
    run.status = "running"
    run.rows_in = 0
    run.rows_loaded = 0
    run.error = None
    return run


class _GoodPipeline(BoletinPipeline):
    """Minimal concrete pipeline that always succeeds."""

    name = "test_pipeline"
    source_id = "test_source"

    async def extract(self) -> list[dict]:
        return [{"id": 1}, {"id": 2}, {"id": 3}]

    async def transform(self, raw_data: list[dict]) -> list[dict]:
        return [{"id": r["id"], "processed": True} for r in raw_data]

    async def load(self, transformed: list[dict]) -> None:
        self.rows_loaded = len(transformed)


class _FailPipeline(BoletinPipeline):
    """Concrete pipeline that always raises during extract."""

    name = "fail_pipeline"
    source_id = "fail_source"

    async def extract(self) -> list[dict]:
        raise RuntimeError("simulated extract failure")

    async def transform(self, raw_data: list[dict]) -> list[dict]:
        return raw_data

    async def load(self, transformed: list[dict]) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests: class-level contract
# ---------------------------------------------------------------------------


class TestBoletinPipelineContract:
    def test_instantiation_requires_name(self):
        """Subclass without 'name' attribute raises TypeError."""

        class _NoName(BoletinPipeline):
            source_id = "x"

            async def extract(self):
                return []

            async def transform(self, raw):
                return raw

            async def load(self, transformed):
                pass

        with pytest.raises(TypeError, match="name"):
            _NoName(db=AsyncMock())

    def test_instantiation_requires_source_id(self):
        """Subclass without 'source_id' attribute raises TypeError."""

        class _NoSource(BoletinPipeline):
            name = "x"

            async def extract(self):
                return []

            async def transform(self, raw):
                return raw

            async def load(self, transformed):
                pass

        with pytest.raises(TypeError, match="source_id"):
            _NoSource(db=AsyncMock())

    def test_default_config_is_empty_dict(self):
        db = _make_db()
        pipeline = _GoodPipeline(db=db)
        assert pipeline.config == {}

    def test_custom_config_stored(self):
        db = _make_db()
        cfg = {"batch_size": 5}
        pipeline = _GoodPipeline(db=db, config=cfg)
        assert pipeline.config == cfg


# ---------------------------------------------------------------------------
# Tests: run() orchestration
# ---------------------------------------------------------------------------


class TestBoletinPipelineRun:
    @pytest.fixture
    def db(self):
        return _make_db()

    @pytest.fixture
    def run_record(self):
        return _make_run()

    async def test_successful_run_returns_loaded_result(self, db, run_record):
        pipeline = _GoodPipeline(db=db)

        with patch.object(pipeline, "_create_ingestion_run", AsyncMock(return_value=run_record)):
            with patch.object(pipeline, "_complete_run", AsyncMock()) as mock_complete:
                result = await pipeline.run()

        assert result.status == "loaded"
        assert result.rows_in == 3
        assert result.rows_loaded == 3
        assert result.pipeline_name == "test_pipeline"
        assert result.source_id == "test_source"
        assert result.error is None
        mock_complete.assert_awaited_once_with(run_record, "loaded")

    async def test_failed_run_returns_failed_result(self, db, run_record):
        pipeline = _FailPipeline(db=db)

        with patch.object(pipeline, "_create_ingestion_run", AsyncMock(return_value=run_record)):
            with patch.object(pipeline, "_complete_run", AsyncMock()) as mock_complete:
                with pytest.raises(RuntimeError, match="simulated extract failure"):
                    await pipeline.run()

        mock_complete.assert_awaited_once()
        call_status = mock_complete.call_args[0][1]
        assert call_status == "failed"

    async def test_run_sets_finished_at(self, db, run_record):
        pipeline = _GoodPipeline(db=db)

        with patch.object(pipeline, "_create_ingestion_run", AsyncMock(return_value=run_record)):
            with patch.object(pipeline, "_complete_run", AsyncMock()):
                result = await pipeline.run()

        assert result.finished_at is not None
        assert isinstance(result.finished_at, datetime)

    async def test_run_id_comes_from_ingestion_run(self, db, run_record):
        run_record.id = 42
        pipeline = _GoodPipeline(db=db)

        with patch.object(pipeline, "_create_ingestion_run", AsyncMock(return_value=run_record)):
            with patch.object(pipeline, "_complete_run", AsyncMock()):
                result = await pipeline.run()

        assert result.run_id == 42


# ---------------------------------------------------------------------------
# Tests: PipelineResult helpers
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_duration_seconds_when_both_timestamps(self):
        r = PipelineResult(
            pipeline_name="p",
            source_id="s",
            status="loaded",
            started_at=datetime(2026, 3, 10, 12, 0, 0),
            finished_at=datetime(2026, 3, 10, 12, 0, 30),
        )
        assert r.duration_seconds == pytest.approx(30.0)

    def test_duration_seconds_none_when_no_finished_at(self):
        r = PipelineResult(
            pipeline_name="p",
            source_id="s",
            status="running",
            started_at=datetime(2026, 3, 10, 12, 0, 0),
        )
        assert r.duration_seconds is None
