"""Interface definitions for the House Helper pipeline.

This module contains Protocol definitions (structural subtyping) for all
pipeline components. Implementations live in services/.
"""

from .data_source import IDataSource
from .filter import FilterCriteria, IFilter

__all__ = [
    "IFilter",
    "FilterCriteria",
    "IDataSource",
]
