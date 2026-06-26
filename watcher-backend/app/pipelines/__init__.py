"""
Watcher Pipeline ABC — Extract → Transform → Load with IngestionRun tracking.

Inspired by br/acc's Pipeline pattern (etl/src/bracc_etl/base.py).
"""

from .base import BoletinPipeline, PipelineResult
from .provincial import ProvincialPipeline
from .uploaded import UploadedPipeline

__all__ = ["BoletinPipeline", "PipelineResult", "ProvincialPipeline", "UploadedPipeline"]
