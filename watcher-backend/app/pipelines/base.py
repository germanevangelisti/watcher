"""
BoletinPipeline — Abstract base class for all Watcher ETL pipelines.

Contract: extract() → transform() → load()
Each run is tracked as an IngestionRun record in the database.

Usage:
    class MyPipeline(BoletinPipeline):
        name = "my_pipeline"
        source_id = "my_source"

        async def extract(self): ...
        async def transform(self, raw_data): ...
        async def load(self, transformed): ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IngestionRun

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Summarises the outcome of a pipeline run."""

    pipeline_name: str
    source_id: str
    status: str  # "loaded" | "failed"
    rows_in: int = 0
    rows_loaded: int = 0
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    run_id: Optional[int] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class BoletinPipeline(ABC):
    """
    Abstract base for all Watcher ingestion pipelines.

    Subclasses must define:
        name       — unique pipeline identifier (e.g. "provincial_boletin")
        source_id  — logical source (e.g. "boletinoficial.cba.gov.ar")

    And implement:
        extract()         → List[dict]
        transform(raw)    → List[dict]
        load(transformed) → None
    """

    name: str
    source_id: str

    def __init__(self, db: AsyncSession, config: Optional[Dict[str, Any]] = None) -> None:
        if not hasattr(self, "name") or not self.name:
            raise TypeError(f"{type(self).__name__} must define class attribute 'name'")
        if not hasattr(self, "source_id") or not self.source_id:
            raise TypeError(f"{type(self).__name__} must define class attribute 'source_id'")

        self.db = db
        self.config = config or {}
        self.rows_in = 0
        self.rows_loaded = 0

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def extract(self) -> List[dict]:
        """Download / read raw data. Returns a list of raw records."""

    @abstractmethod
    async def transform(self, raw_data: List[dict]) -> List[dict]:
        """Clean, enrich and normalise raw records. Returns transformed records."""

    @abstractmethod
    async def load(self, transformed: List[dict]) -> None:
        """Persist transformed records to SQL / Graph / Vector store."""

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def run(self) -> PipelineResult:
        """
        Execute the full pipeline and return a PipelineResult.

        Automatically creates and updates an IngestionRun record.
        """
        run_record = await self._create_ingestion_run()
        result = PipelineResult(
            pipeline_name=self.name,
            source_id=self.source_id,
            status="running",
            started_at=run_record.started_at,
            run_id=run_record.id,
        )

        try:
            logger.info("[%s] Starting extract phase", self.name)
            raw = await self.extract()
            self.rows_in = len(raw)

            logger.info("[%s] Starting transform phase (%d records)", self.name, self.rows_in)
            transformed = await self.transform(raw)

            logger.info("[%s] Starting load phase (%d records)", self.name, len(transformed))
            await self.load(transformed)
            self.rows_loaded = len(transformed)

            result.status = "loaded"
            result.rows_in = self.rows_in
            result.rows_loaded = self.rows_loaded
            await self._complete_run(run_record, "loaded")
            logger.info(
                "[%s] Completed: %d/%d records loaded", self.name, self.rows_loaded, self.rows_in
            )

        except Exception as exc:
            error_msg = str(exc)
            result.status = "failed"
            result.rows_in = self.rows_in
            result.error = error_msg
            await self._complete_run(run_record, "failed", error=error_msg)
            logger.error("[%s] Failed: %s", self.name, error_msg, exc_info=True)
            raise

        finally:
            result.finished_at = datetime.utcnow()

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _create_ingestion_run(self) -> IngestionRun:
        run = IngestionRun(
            pipeline_name=self.name,
            source_id=self.source_id,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def _complete_run(
        self,
        run: IngestionRun,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        run.status = status
        run.rows_in = self.rows_in
        run.rows_loaded = self.rows_loaded
        run.error = error
        run.finished_at = datetime.utcnow()
        await self.db.commit()
