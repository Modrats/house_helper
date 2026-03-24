"""HouseRepository — domain layer wrapping IDataSource.

Translates between the generic storage interface (IDataSource) and
house-domain operations. All knowledge of path conventions, file
formats, and pipeline-resume logic lives here.

Keeping this logic out of LocalStorage (and any future cloud storage
implementation) means the storage layer stays as pure CRUD — only this
repository needs to change when the house data shape evolves.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..interfaces.data_source import IDataSource
from ..models.house import FilterResult, House, HouseStatus
from ..models.room import Photo
from ..observability import get_logger

logger = get_logger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class HouseRepository:
    """Domain repository for house data.

    Wraps IDataSource to provide house-specific read/write operations.
    All path construction lives here; the storage layer only handles
    raw bytes and JSON serialisation.

    Args:
        storage: Generic storage backend (e.g. LocalStorage).
        input_dir: Root directory for input house data.
        output_dir: Root directory for pipeline outputs.
    """

    def __init__(
        self,
        storage: IDataSource,
        input_dir: Path,
        output_dir: Path,
    ) -> None:
        self._storage = storage
        self._input_dir = input_dir
        self._output_dir = output_dir

    # -- Pipeline methods -------------------------------------------------------

    def load_houses(self, criteria: dict[str, Any]) -> list[House]:
        """Load all houses, restoring status from existing outputs.

        If a house has saved filter results but criteria have changed
        since the last run, its status is reset to RAW for re-processing.

        Args:
            criteria: Current filter criteria from config, used to detect drift.

        Returns:
            List of houses with status restored from prior outputs.
        """
        houses: list[House] = []
        for key in self._storage.list_keys(self._input_dir):
            house_dir = Path(key)
            listing_file = house_dir / "listing.txt"
            if not self._storage.exists(listing_file):
                continue

            listing_text = self._storage.read_bytes(listing_file).decode("utf-8").strip()
            status, filter_results = self._restore_filter_state(house_dir.name, criteria)
            houses.append(
                House(
                    slug=house_dir.name,
                    listing_text=listing_text,
                    status=status,
                    filter_results=filter_results,
                )
            )
        return houses

    def save_filter_results(self, houses: list[House]) -> None:
        """Write filter results for each house to output storage.

        Args:
            houses: Houses with filter_results populated by the pipeline.
        """
        for house in houses:
            output_path = self._output_dir / house.slug / "criteria" / "filter_result.json"
            self._storage.write_json(
                output_path,
                house.model_dump(include={"slug", "status", "filter_results"}),
            )

    # -- Query methods (API layer) ----------------------------------------------

    def list_houses(self) -> list[str]:
        """List all available house slugs."""
        return sorted(
            Path(key).name
            for key in self._storage.list_keys(self._input_dir)
            if self._storage.exists(Path(key) / "listing.txt")
        )

    def get_house(self, slug: str) -> House:
        """Load a single house with its metadata, listing text, and photos.

        Raises:
            FileNotFoundError: If the house slug does not exist.
        """
        house_dir = self._input_dir / slug
        listing_file = house_dir / "listing.txt"
        if not self._storage.exists(listing_file):
            raise FileNotFoundError(f"House '{slug}' not found")

        listing_text = self._storage.read_bytes(listing_file).decode("utf-8").strip()

        filter_output = self._output_dir / slug / "criteria" / "filter_result.json"
        filter_results = FilterResult()
        status = HouseStatus.RAW
        if self._storage.exists(filter_output):
            saved = self._storage.read_json(filter_output)
            status = HouseStatus(saved.get("status", "raw"))
            filter_results = FilterResult(**saved.get("filter_results", {}))

        photos: list[Photo] = []
        photos_dir = house_dir / "photos"
        if self._storage.exists(photos_dir):
            for key in self._storage.list_keys(photos_dir):
                f = Path(key)
                if f.suffix.lower() in _IMAGE_EXTENSIONS:
                    photos.append(
                        Photo(filename=f.name, path=str(f.relative_to(self._input_dir)))
                    )

        return House(
            slug=slug,
            listing_text=listing_text,
            status=status,
            filter_results=filter_results,
            photos=photos,
        )

    def get_photos(self, slug: str) -> list[str]:
        """Get absolute file path strings for all photos of a house.

        Raises:
            FileNotFoundError: If the house slug does not exist.
        """
        house_dir = self._input_dir / slug
        if not self._storage.exists(house_dir):
            raise FileNotFoundError(f"House '{slug}' not found")

        photos_dir = house_dir / "photos"
        return [
            key
            for key in self._storage.list_keys(photos_dir)
            if Path(key).suffix.lower() in _IMAGE_EXTENSIONS
        ]

    def get_room_classifications(self, slug: str) -> dict[str, list[str]]:
        """Get room-to-photo mappings from classifier output."""
        classifications_file = self._output_dir / slug / "classifications.json"
        if not self._storage.exists(classifications_file):
            return {}
        return self._storage.read_json(classifications_file)

    def get_criteria_results(self, slug: str) -> FilterResult:
        """Get criteria pass/fail results from pipeline output."""
        filter_output = self._output_dir / slug / "criteria" / "filter_result.json"
        if not self._storage.exists(filter_output):
            return FilterResult()
        saved = self._storage.read_json(filter_output)
        return FilterResult(**saved.get("filter_results", {}))

    def get_imagineered_photos(self, slug: str) -> list[str]:
        """Get absolute file path strings for imagineered (AI-reimagined) photos."""
        imagineered_dir = self._output_dir / slug / "imagineered"
        return [
            key
            for key in self._storage.list_keys(imagineered_dir)
            if Path(key).suffix.lower() in _IMAGE_EXTENSIONS
        ]

    def get_photo_bytes(self, slug: str, filename: str) -> bytes:
        """Read raw bytes for an input photo.

        Raises:
            FileNotFoundError: If the photo does not exist.
        """
        path = self._input_dir / slug / "photos" / filename
        if not self._storage.exists(path):
            raise FileNotFoundError(f"Photo '{filename}' not found for house '{slug}'")
        return self._storage.read_bytes(path)

    def get_imagineered_photo_bytes(self, slug: str, filename: str) -> bytes:
        """Read raw bytes for an imagineered output photo.

        Raises:
            FileNotFoundError: If the imagineered photo does not exist.
        """
        path = self._output_dir / slug / "imagineered" / filename
        if not self._storage.exists(path):
            raise FileNotFoundError(
                f"Imagineered photo '{filename}' not found for house '{slug}'"
            )
        return self._storage.read_bytes(path)

    # -- Private helpers --------------------------------------------------------

    def _restore_filter_state(
        self,
        slug: str,
        criteria: dict[str, Any],
    ) -> tuple[HouseStatus, FilterResult]:
        """Restore status and filter results from a previous pipeline run.

        Returns (RAW, empty FilterResult) if no prior output exists or if
        the saved criteria no longer match the current config (drift detection).
        """
        filter_output = self._output_dir / slug / "criteria" / "filter_result.json"
        if not self._storage.exists(filter_output):
            return HouseStatus.RAW, FilterResult()

        saved = self._storage.read_json(filter_output)
        if not self._criteria_match(saved, criteria):
            logger.info("Criteria changed for '%s', re-processing", slug)
            return HouseStatus.RAW, FilterResult()

        status = HouseStatus(saved.get("status", "raw"))
        filter_results = FilterResult(**saved.get("filter_results", {}))
        return status, filter_results

    @staticmethod
    def _criteria_match(
        saved: dict[str, Any],
        current_criteria: dict[str, Any],
    ) -> bool:
        """Check if saved filter results cover the same criteria as the current config.

        Detects criteria drift: if the config has changed since the last run,
        saved results are stale and the house must be re-processed.

        Args:
            saved: Parsed JSON from a prior filter_result.json.
            current_criteria: Current criteria dict from config.

        Returns:
            True if the criteria keys still match.
        """
        saved_fr = saved.get("filter_results", {})
        saved_p1 = set(saved_fr.get("p1", {}).keys())
        saved_p2 = set(saved_fr.get("p2", {}).keys())
        saved_excl = set(saved_fr.get("excluded", {}).keys())

        current_p1 = set(current_criteria.get("p1_keywords", []))
        current_p2 = set(current_criteria.get("p2_keywords", []))
        current_excl = set(current_criteria.get("excluded_keywords", []))

        return saved_p1 == current_p1 and saved_p2 == current_p2 and saved_excl == current_excl
