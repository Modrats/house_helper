"""Interface definitions for the House Helper pipeline.

This module contains ABC definitions for all pipeline components.
Implementations live in services/.
"""

from .data_source import IDataSource
from .filter import IFilter

__all__ = [
    "IFilter",
    "IDataSource",
]
