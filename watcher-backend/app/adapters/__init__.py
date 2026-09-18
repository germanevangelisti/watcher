"""
Adapters package - Data Integration Adapters (DIA Layer)

This package contains adapters that normalize data from different sources
into a common schema for processing by the AI agents.
"""

from .base_adapter import AdapterResult, BaseAdapter, DocumentSchema
from .ppa import PersistenceAdapter
from .sca_prov import ProvincialAdapter

__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "DocumentSchema",
    "ProvincialAdapter",
    "PersistenceAdapter",
]
