"""
Adapters package - Data Integration Adapters (DIA Layer)

This package contains adapters that normalize data from different sources
into a common schema for processing by the AI agents.
"""

from .base_adapter import BaseAdapter, AdapterResult, DocumentSchema
from .sca_prov import ProvincialAdapter
from .ppa import PersistenceAdapter

__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "DocumentSchema",
    "ProvincialAdapter",
    "PersistenceAdapter",
]
