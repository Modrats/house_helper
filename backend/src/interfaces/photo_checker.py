"""IPhotoChecker abstract base class for photo criteria checking."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models.photo_criteria import PhotoCriteriaResult


class IPhotoChecker(ABC):
    """Abstract base class for checking room photos against visual criteria."""

    @abstractmethod
    def check_house(self, slug: str) -> PhotoCriteriaResult:
        """Check all rooms in a house against configured photo criteria.

        Reads room classifications to determine room types, then evaluates
        each photo against the required and preferred features for that
        room type.

        Args:
            slug: House identifier (folder name under input_dir/houses/).

        Returns:
            PhotoCriteriaResult with per-room feature evaluations.
        """
