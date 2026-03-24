"""Pipeline runners and entry points.

Each runner is an executable entry point that wires up the pipeline
and executes it. Runners use core.py for dependency injection.
"""

from .run_pipeline import FilterPipeline

__all__ = [
    "FilterPipeline",
]
