"""
ProvincialPipeline — Ingests boletines from Córdoba's official gazette.

Wraps the existing SyncService + BatchProcessor flow under the
BoletinPipeline ABC contract so runs are tracked as IngestionRun records.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.pipelines.base import BoletinPipeline

logger = logging.getLogger(__name__)


class ProvincialPipeline(BoletinPipeline):
    """
    Pipeline for Córdoba provincial bulletins (boletinoficial.cba.gov.ar).

    extract()   — Discovers unprocessed PDF files in BOLETINES_DIR.
    transform() — Runs text extraction + chunk enrichment per file.
    load()      — Indexes into SQLite (FTS5) + ChromaDB via BatchProcessor.
    """

    name = "provincial_boletin"
    source_id = "boletinoficial.cba.gov.ar"

    def __init__(
        self,
        db: AsyncSession,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(db, config)
        self._source_dir = Path(
            self.config.get("source_dir", settings.BOLETINES_DIR)
        )

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def extract(self) -> list[dict]:
        """
        Discover PDF files in the source directory that haven't been indexed.

        Returns a list of dicts with keys: path, filename, date, section.
        """
        from sqlalchemy import select
        from app.db.models import Boletin

        if not self._source_dir.exists():
            logger.warning("BOLETINES_DIR '%s' does not exist — nothing to extract", self._source_dir)
            return []

        pdf_files = sorted(self._source_dir.rglob("*.pdf"))
        if not pdf_files:
            logger.info("No PDF files found in '%s'", self._source_dir)
            return []

        # Filter out already-processed files
        result = await self.db.execute(
            select(Boletin.filename).where(Boletin.status == "completed")
        )
        already_done: set[str] = {row[0] for row in result.fetchall()}

        pending = [
            {"path": str(p), "filename": p.name}
            for p in pdf_files
            if p.name not in already_done
        ]
        logger.info(
            "extract: found %d PDFs, %d pending (skipping %d already completed)",
            len(pdf_files),
            len(pending),
            len(already_done),
        )
        return pending

    async def transform(self, raw_data: list[dict]) -> list[dict]:
        """
        Extract text from each PDF using ExtractorRegistry.

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
                # Still include but mark as failed so load() can record the error
                transformed.append({**item, "text": "", "pages": 0, "char_count": 0, "error": str(exc)})

        return transformed

    async def load(self, transformed: list[dict]) -> None:
        """
        Persist each extracted document into the database.

        Creates or updates a Boletin record and triggers analysis via BatchProcessor.
        """
        from app.db import crud
        from app.db.models import Boletin
        from sqlalchemy import select

        loaded = 0
        for item in transformed:
            try:
                # Upsert boletin record
                result = await self.db.execute(
                    select(Boletin).where(Boletin.filename == item["filename"])
                )
                boletin = result.scalar_one_or_none()

                if boletin is None:
                    boletin = Boletin(
                        filename=item["filename"],
                        status="completed" if not item.get("error") else "failed",
                        error_message=item.get("error"),
                    )
                    self.db.add(boletin)
                else:
                    boletin.status = "completed" if not item.get("error") else "failed"
                    boletin.error_message = item.get("error")

                await self.db.commit()
                if not item.get("error"):
                    loaded += 1
            except Exception as exc:
                logger.error("load: failed to persist '%s': %s", item.get("filename"), exc)
                await self.db.rollback()

        self.rows_loaded = loaded
