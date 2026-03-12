"""
sources.py — Data source registry endpoint.

Exposes GET /sources/health which returns the list of configured data sources
from config/source_registry.yml along with their enabled status.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4] / "config" / "source_registry.yml"
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SourceEntry(BaseModel):
    id: str
    name: str
    type: str
    url: Optional[str] = None
    jurisdiccion: Optional[str] = None
    schedule: Optional[str] = None
    enabled: bool = True
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class SourcesHealthResponse(BaseModel):
    total: int
    enabled: int
    disabled: int
    sources: List[SourceEntry]


# ---------------------------------------------------------------------------
# Loader (cached at module level to avoid repeated disk reads)
# ---------------------------------------------------------------------------

_REGISTRY_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_registry() -> List[Dict[str, Any]]:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    if not _REGISTRY_PATH.is_file():
        logger.warning("source_registry.yml not found at %s", _REGISTRY_PATH)
        _REGISTRY_CACHE = []
        return _REGISTRY_CACHE

    try:
        raw = _REGISTRY_PATH.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        _REGISTRY_CACHE = data.get("sources", []) if data else []
    except Exception as exc:
        logger.error("Failed to load source_registry.yml: %s", exc)
        # Do not cache on error — next request will retry
        return []

    return _REGISTRY_CACHE


def _clear_registry_cache() -> None:
    """Clear the in-memory cache (useful in tests)."""
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/health", response_model=SourcesHealthResponse)
async def sources_health() -> SourcesHealthResponse:
    """
    Return the list of configured data sources and their enabled status.

    Reads from config/source_registry.yml. The registry is cached in memory
    after the first request.
    """
    raw_sources = _load_registry()

    sources: List[SourceEntry] = []
    for entry in raw_sources:
        try:
            sources.append(SourceEntry(**entry))
        except Exception as exc:
            logger.warning("Skipping malformed source entry %s: %s", entry, exc)

    enabled_count = sum(1 for s in sources if s.enabled)
    return SourcesHealthResponse(
        total=len(sources),
        enabled=enabled_count,
        disabled=len(sources) - enabled_count,
        sources=sources,
    )
