"""
🔍 WATCHER DATA SCIENCE LAB
Sistema modular para análisis de transparencia gubernamental
"""

__version__ = "2.0.0"
__author__ = "Watcher Team"
__description__ = "Sistema agentic para detección de irregularidades en boletines oficiales"

from .extractors.entity_extractor import WatcherEntityExtractor
from .analyzers.false_positive_detector import FalsePositiveDetector

__all__ = [
    "WatcherEntityExtractor",
    "FalsePositiveDetector"
]
