"""IImagineeringService abstract base class for room image reimagining."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.imagineering import ImagineeringResult


class IImagineeringService(ABC):
    """Abstract base class for room imagineering operations."""

    @abstractmethod
    def imagineer_house(self, slug: str) -> ImagineeringResult:
        """Reimagine all classified rooms for a single house.

        Reads room classifications from the output directory, generates
        reimagined images using a generative model, and saves results.

        Args:
            slug: House identifier (folder name under input_dir/houses/).

        Returns:
            ImagineeringResult with per-photo generation results.
        """
