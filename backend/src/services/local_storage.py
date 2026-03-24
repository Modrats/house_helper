"""Local filesystem implementation of IDataSource.

Reads house data from slug-based directory structure under input_dir.
Persists and restores pipeline outputs under output_dir.
Handles resume detection and criteria drift validation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..interfaces.data_source import IDataSource
from ..models.house import FilterResult, House, HouseStatus

logger = logging.getLogger(__name__)


class LocalStorage(IDataSource):
    """Reads houses from local filesystem and persists pipeline outputs.

    Args:
        input_dir: Root directory containing house folders with listing.txt.
        output_dir: Root directory for writing pipeline output files.
    """

    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        self._input_dir = input_dir
        self._output_dir = output_dir

    def load_houses(self, criteria: dict[str, Any]) -> list[House]:
        """Load all houses, restoring status from existing outputs.

        If a house has saved filter results but the criteria have changed
        since the last run, its status is reset to RAW for re-processing.

        Args:
            criteria: Current filter criteria from config, used to detect drift.

        Returns:
            List of houses with status restored from any prior outputs.
        """
        houses: list[House] = []
        if not self._input_dir.exists():
            return houses

        for house_dir in sorted(self._input_dir.iterdir()):
            listing_file = house_dir / "listing.txt"
            if not listing_file.exists():
                continue

            listing_text = listing_file.read_text(encoding="utf-8").strip()
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
        """Write filter results for each house.

        Args:
            houses: Houses with filter_results populated by the pipeline.
        """
        for house in houses:
            output_dir = self._output_dir / house.slug / "criteria"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / "filter_result.json"
            output_file.write_text(
                json.dumps(
                    house.model_dump(include={"slug", "status", "filter_results"}),
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    def _restore_filter_state(
        self,
        slug: str,
        criteria: dict[str, Any],
    ) -> tuple[HouseStatus, FilterResult]:
        """Restore status and filter results from a previous run.

        Returns (RAW, empty FilterResult) if no prior output exists
        or if the saved criteria no longer match the current config.

        Args:
            slug: House folder name.
            criteria: Current criteria for drift comparison.

        Returns:
            Tuple of (status, filter_results) from prior output.
        """
        filter_output = self._output_dir / slug / "criteria" / "filter_result.json"

        if not filter_output.exists():
            return HouseStatus.RAW, FilterResult()

        saved = json.loads(filter_output.read_text(encoding="utf-8"))

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
        """Check if saved filter_results cover the same criteria as current config.

        Compares the p1/p2/excluded keys in the saved output against the
        keyword lists in the current criteria YAML.

        Args:
            saved: Parsed JSON from a prior filter_result.json.
            current_criteria: Current criteria dict from config.

        Returns:
            True if the criteria keys match.
        """
        saved_fr = saved.get("filter_results", {})
        saved_p1 = set(saved_fr.get("p1", {}).keys())
        saved_p2 = set(saved_fr.get("p2", {}).keys())
        saved_excl = set(saved_fr.get("excluded", {}).keys())

        current_p1 = set(current_criteria.get("p1_keywords", []))
        current_p2 = set(current_criteria.get("p2_keywords", []))
        current_excl = set(current_criteria.get("excluded_keywords", []))

        return saved_p1 == current_p1 and saved_p2 == current_p2 and saved_excl == current_excl
