"""
Pipeline Runs endpoint — Lists and inspects IngestionRun records.

GET  /api/v1/pipelines/runs           — Paginated list of all runs
GET  /api/v1/pipelines/runs/{run_id}  — Single run detail
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IngestionRun
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class IngestionRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pipeline_name: str
    source_id: str
    status: str
    rows_in: int = 0
    rows_loaded: int = 0
    error: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class PaginatedRunsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[IngestionRunSchema]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/runs", response_model=PaginatedRunsResponse, summary="List pipeline runs")
async def list_pipeline_runs(
    pipeline_name: Optional[str] = Query(None, description="Filter by pipeline name"),
    status: Optional[str] = Query(None, description="Filter by status (running|loaded|failed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRunsResponse:
    """
    Return a paginated list of IngestionRun records, newest first.

    Filters: `pipeline_name`, `status`.
    """
    stmt = select(IngestionRun)

    if pipeline_name:
        stmt = stmt.where(IngestionRun.pipeline_name == pipeline_name)
    if status:
        stmt = stmt.where(IngestionRun.status == status)

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    stmt = stmt.order_by(IngestionRun.started_at.desc()).offset(offset).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedRunsResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[IngestionRunSchema.model_validate(r) for r in rows],
    )


@router.get("/runs/{run_id}", response_model=IngestionRunSchema, summary="Get a single pipeline run")
async def get_pipeline_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> IngestionRunSchema:
    """Return details for a specific IngestionRun by its ID."""
    result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail=f"IngestionRun {run_id} not found")

    return IngestionRunSchema.model_validate(run)
