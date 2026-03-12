"""
UploadedPipeline — Ingests documents uploaded manually via the API.

Wraps the upload → extract → index flow under the BoletinPipeline ABC
contract so each upload batch is tracked as an IngestionRun record.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.pipelines.base import BoletinPipeline

logger = logging.getLogger(__name__)


class UploadedPipeline(BoletinPipeline):
    """
    Pipeline for documents uploaded manually through the /upload API endpoint.

    extract()   — Reads file paths from the config['files'] list.
    transform() — Runs text extraction via ExtractorRegistry.
    load()      — Indexes into SQLite + ChromaDB via IndexingService.
    """

    name = "uploaded_document"
    source_id = "manual_upload"

    def __init__(
        self,
        db: AsyncSession,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(db, config)
        # config['files'] must be a list of file path strings
        self._files: list[str] = self.config.get("files", [])

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def extract(self) -> list[dict]:
        """
        Build raw record list from the provided file paths.

        Returns dicts with keys: path, filename.
        """
        records: list[dict] = []
        for file_path_str in self._files:
            path = Path(file_path_str)
            if not path.exists():
                logger.warning("extract: file not found '%s' — skipping", path)
                continue
            records.append({"path": str(path), "filename": path.name})

        logger.info("extract: %d/%d files found", len(records), len(self._files))
        return records

    async def transform(self, raw_data: list[dict]) -> list[dict]:
        """
        Extract text from each uploaded file using ExtractorRegistry.

        Adds 'text', 'pages', and 'char_count' to each record.
        """
        from app.services.extractors import ExtractorRegistry

        transformed: list[dict] = []
        for item in raw_data:
            path = Path(item["path"])
            try:
                extraction = await ExtractorRegistry.extract(path)
                transformed.append(
                    {
                        **item,
                        "text": extraction.get("text", ""),
                        "pages": extraction.get("pages", 0),
                        "char_count": len(extraction.get("text", "")),
                    }
                )
            except Exception as exc:
                logger.warning("transform: failed to extract '%s': %s", path.name, exc)
                transformed.append(
                    {**item, "text": "", "pages": 0, "char_count": 0, "error": str(exc)}
                )

        return transformed

    async def load(self, transformed: list[dict]) -> None:
        """
        Persist extracted documents via IndexingService.

        Each document is triple-indexed: ChromaDB + SQLite + FTS5.
        """
        try:
            from app.services.indexing_service import get_indexing_service
            indexing = get_indexing_service()
        except Exception as exc:
            logger.error("load: IndexingService unavailable: %s", exc)
            raise

        loaded = 0
        for item in transformed:
            if item.get("error") or not item.get("text"):
                logger.warning("load: skipping '%s' (no text or extraction error)", item["filename"])
                continue
            try:
                await indexing.index_document(
                    document_id=item["filename"],
                    text=item["text"],
                    metadata={
                        "source": "manual_upload",
                        "filename": item["filename"],
                        "pages": item.get("pages", 0),
                        "char_count": item.get("char_count", 0),
                    },
                )
                loaded += 1
            except Exception as exc:
                logger.error("load: failed to index '%s': %s", item["filename"], exc)

        self.rows_loaded = loaded
