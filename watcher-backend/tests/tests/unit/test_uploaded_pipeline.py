"""
Unit tests for UploadedPipeline.

All file-system and service interactions are mocked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipelines.uploaded import UploadedPipeline


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


class TestUploadedPipelineMeta:
    def test_name_and_source_id(self):
        assert UploadedPipeline.name == "uploaded_document"
        assert UploadedPipeline.source_id == "manual_upload"

    def test_files_from_config(self):
        db = _make_db()
        files = ["/tmp/a.pdf", "/tmp/b.pdf"]
        pipeline = UploadedPipeline(db=db, config={"files": files})
        assert pipeline._files == files

    def test_empty_files_when_no_config(self):
        db = _make_db()
        pipeline = UploadedPipeline(db=db)
        assert pipeline._files == []


class TestUploadedPipelineExtract:
    async def test_extract_returns_existing_files(self, tmp_path):
        f1 = tmp_path / "doc1.pdf"
        f2 = tmp_path / "doc2.pdf"
        f1.write_bytes(b"%PDF")
        f2.write_bytes(b"%PDF")

        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": [str(f1), str(f2)]})
        result = await pipeline.extract()

        assert len(result) == 2
        filenames = {r["filename"] for r in result}
        assert "doc1.pdf" in filenames
        assert "doc2.pdf" in filenames

    async def test_extract_skips_missing_files(self, tmp_path):
        real = tmp_path / "real.pdf"
        real.write_bytes(b"%PDF")
        missing = tmp_path / "ghost.pdf"

        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": [str(real), str(missing)]})
        result = await pipeline.extract()

        assert len(result) == 1
        assert result[0]["filename"] == "real.pdf"

    async def test_extract_empty_when_no_files(self):
        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": []})
        result = await pipeline.extract()
        assert result == []


class TestUploadedPipelineTransform:
    async def test_transform_adds_text_and_pages(self, tmp_path):
        pdf = tmp_path / "upload.pdf"
        pdf.write_bytes(b"%PDF")
        raw = [{"path": str(pdf), "filename": "upload.pdf"}]

        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": [str(pdf)]})

        with patch(
            "app.services.extractors.ExtractorRegistry.extract",
            AsyncMock(return_value={"text": "texto extraído", "pages": 3}),
        ):
            result = await pipeline.transform(raw)

        assert result[0]["text"] == "texto extraído"
        assert result[0]["pages"] == 3
        assert result[0]["char_count"] == len("texto extraído")

    async def test_transform_marks_error_on_failure(self, tmp_path):
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"not a pdf")
        raw = [{"path": str(pdf), "filename": "bad.pdf"}]

        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": [str(pdf)]})

        with patch(
            "app.services.extractors.ExtractorRegistry.extract",
            AsyncMock(side_effect=Exception("parse error")),
        ):
            result = await pipeline.transform(raw)

        assert result[0]["error"] == "parse error"
        assert result[0]["text"] == ""


class TestUploadedPipelineLoad:
    async def test_load_calls_indexing_service(self, tmp_path):
        transformed = [
            {"filename": "doc.pdf", "text": "contenido", "pages": 1, "char_count": 9}
        ]

        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": []})

        mock_indexing = MagicMock()
        mock_indexing.index_document = AsyncMock()

        with patch("app.services.indexing_service.get_indexing_service", return_value=mock_indexing):
            await pipeline.load(transformed)

        mock_indexing.index_document.assert_awaited_once()
        call_kwargs = mock_indexing.index_document.call_args[1]
        assert call_kwargs["document_id"] == "doc.pdf"
        assert call_kwargs["text"] == "contenido"
        assert pipeline.rows_loaded == 1

    async def test_load_skips_empty_text(self, tmp_path):
        transformed = [
            {"filename": "empty.pdf", "text": "", "pages": 0, "char_count": 0}
        ]

        db = _make_db()
        pipeline = UploadedPipeline(db=db, config={"files": []})

        mock_indexing = MagicMock()
        mock_indexing.index_document = AsyncMock()

        with patch("app.services.indexing_service.get_indexing_service", return_value=mock_indexing):
            await pipeline.load(transformed)

        mock_indexing.index_document.assert_not_awaited()
        assert pipeline.rows_loaded == 0
