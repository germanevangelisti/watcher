"""
Unit tests for ProvincialPipeline.

All file-system and database interactions are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipelines.provincial import ProvincialPipeline


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


class TestProvincialPipelineMeta:
    def test_name_and_source_id(self):
        assert ProvincialPipeline.name == "provincial_boletin"
        assert ProvincialPipeline.source_id == "boletinoficial.cba.gov.ar"

    def test_custom_source_dir_from_config(self, tmp_path):
        db = _make_db()
        pipeline = ProvincialPipeline(db=db, config={"source_dir": str(tmp_path)})
        assert pipeline._source_dir == tmp_path


class TestProvincialPipelineExtract:
    async def test_returns_empty_when_dir_missing(self, tmp_path):
        db = _make_db()
        pipeline = ProvincialPipeline(db=db, config={"source_dir": str(tmp_path / "nonexistent")})

        # DB query returns no completed boletines
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        result = await pipeline.extract()
        assert result == []

    async def test_returns_pending_pdfs(self, tmp_path):
        # Create two PDFs
        (tmp_path / "boletin_1.pdf").write_bytes(b"%PDF-1")
        (tmp_path / "boletin_2.pdf").write_bytes(b"%PDF-1")
        (tmp_path / "boletin_completed.pdf").write_bytes(b"%PDF-1")

        db = _make_db()
        pipeline = ProvincialPipeline(db=db, config={"source_dir": str(tmp_path)})

        # Simulate boletin_completed.pdf already done
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("boletin_completed.pdf",)]
        db.execute = AsyncMock(return_value=mock_result)

        result = await pipeline.extract()
        filenames = {r["filename"] for r in result}
        assert "boletin_1.pdf" in filenames
        assert "boletin_2.pdf" in filenames
        assert "boletin_completed.pdf" not in filenames

    async def test_returns_empty_when_no_pdfs(self, tmp_path):
        (tmp_path / "notes.txt").write_text("not a pdf")
        db = _make_db()
        pipeline = ProvincialPipeline(db=db, config={"source_dir": str(tmp_path)})

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        result = await pipeline.extract()
        assert result == []


class TestProvincialPipelineTransform:
    async def test_transform_adds_text_field(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1")
        raw = [{"path": str(pdf), "filename": "test.pdf"}]

        db = _make_db()
        pipeline = ProvincialPipeline(db=db, config={"source_dir": str(tmp_path)})

        with patch(
            "app.services.extractors.ExtractorRegistry.extract",
            AsyncMock(return_value={"text": "contenido del boletin", "pages": 2}),
        ):
            result = await pipeline.transform(raw)

        assert len(result) == 1
        assert result[0]["text"] == "contenido del boletin"
        assert result[0]["pages"] == 2
        assert result[0]["char_count"] == len("contenido del boletin")

    async def test_transform_marks_error_on_extraction_failure(self, tmp_path):
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"corrupted")
        raw = [{"path": str(pdf), "filename": "bad.pdf"}]

        db = _make_db()
        pipeline = ProvincialPipeline(db=db, config={"source_dir": str(tmp_path)})

        with patch(
            "app.services.extractors.ExtractorRegistry.extract",
            AsyncMock(side_effect=ValueError("corrupt pdf")),
        ):
            result = await pipeline.transform(raw)

        assert len(result) == 1
        assert result[0]["error"] == "corrupt pdf"
        assert result[0]["text"] == ""
