"""Distance calculator service — calculates travel times via Azure Maps API.

Reads a house address from input_data/houses/{slug}/listing.txt,
queries the Azure Maps API for configured destinations,
and writes results to outputs/houses/{slug}/distances.json.

Idempotent — skips recalculation if results already exist and destinations
config has not changed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import requests

from ..interfaces.distance_calculator import IDistanceCalculator
from ..models.distance import DistanceResult, TravelTime

logger = logging.getLogger(__name__)

_AZURE_MAPS_SEARCH = "https://atlas.microsoft.com/search/address/json"
_AZURE_MAPS_ROUTE = "https://atlas.microsoft.com/route/directions/json"
_REQUEST_TIMEOUT = 30

_AZURE_MODES = {
    "driving": "car",
    "walking": "pedestrian",
    "transit": "bus",
}


class AzureMapsDistanceCalculator(IDistanceCalculator):
    """Calculates travel times via the Azure Maps API.

    Args:
        api_key: Azure Maps subscription key.
        input_dir: Root directory containing house input data.
        output_dir: Root directory for distance output.
        destinations: List of destination configs, each with name, address, modes.
    """

    def __init__(
        self,
        api_key: str,
        input_dir: Path,
        output_dir: Path,
        destinations: list[dict[str, str | list[str]]],
    ) -> None:
        self._api_key = api_key
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._destinations = destinations

    def calculate_distances(self, slug: str) -> DistanceResult:
        """Calculate travel times from a house to all configured destinations.

        Args:
            slug: House identifier (folder name under input_dir/houses/).

        Returns:
            DistanceResult with per-destination travel times.
        """
        output_file = self._output_dir / slug / "distances.json"

        existing = self._load_previous_results(output_file)
        if existing is not None and self._config_matches(existing):
            logger.info("Distances already calculated for '%s' — skipping", slug)
            return DistanceResult(
                slug=slug,
                origin_address=existing.get("origin_address", ""),
                destinations=[TravelTime(**d) for d in existing.get("destinations", [])],
            )

        origin = self._extract_address(slug)
        if not origin:
            logger.warning("No address found for house '%s' — cannot calculate distances", slug)
            return DistanceResult(slug=slug)

        logger.info("Calculating distances for '%s' from '%s'", slug, origin)

        travel_times: list[TravelTime] = []
        for dest in self._destinations:
            dest_name = str(dest["name"])
            dest_address = str(dest["address"])
            modes = dest.get("modes", ["driving"])
            if isinstance(modes, str):
                modes = [modes]

            for mode in modes:
                travel_time = self._query_distance(origin, dest_name, dest_address, str(mode))
                if travel_time is not None:
                    travel_times.append(travel_time)

        result = DistanceResult(
            slug=slug,
            origin_address=origin,
            destinations=travel_times,
        )

        self._save_results(output_file, result)
        logger.info(
            "Calculated %d travel times for '%s'",
            len(travel_times),
            slug,
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_address(self, slug: str) -> str:
        """Extract address from listing.txt for a house.

        Looks for common address patterns in the listing text.
        Falls back to the first non-empty line if no pattern matches.

        Args:
            slug: House identifier.

        Returns:
            Extracted address string, or empty string if not found.
        """
        listing_file = self._input_dir / slug / "listing.txt"
        if not listing_file.exists():
            logger.warning("No listing.txt found for house '%s'", slug)
            return ""

        text = listing_file.read_text(encoding="utf-8").strip()
        if not text:
            return ""

        # Look for "Address:" or "Adres:" line (common in Dutch/English listings)
        for line in text.splitlines():
            stripped = line.strip()
            match = re.match(r"^(?:address|adres|location)\s*[:]\s*(.+)$", stripped, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fall back to first non-empty line (often the address in listing files)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped

        return ""

    def _query_distance(
        self,
        origin: str,
        dest_name: str,
        dest_address: str,
        mode: str,
    ) -> TravelTime | None:
        """Query Azure Maps for a single origin-destination pair.

        Args:
            origin: Origin address string.
            dest_name: Human-readable destination name.
            dest_address: Destination address string.
            mode: Travel mode (driving, walking, transit). Cycling is not supported.

        Returns:
            TravelTime result, or None if the mode is unsupported or an error occurred.
        """
        azure_mode = _AZURE_MODES.get(mode)
        if azure_mode is None:
            logger.warning(
                "Travel mode '%s' is not supported by Azure Maps — skipping '%s'",
                mode,
                dest_name,
            )
            return None

        try:
            origin_lat, origin_lon = self._geocode(origin)
            dest_lat, dest_lon = self._geocode(dest_address)
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "Geocode failed for '%s' -> '%s' (%s): %s",
                origin,
                dest_name,
                mode,
                exc,
            )
            return None

        resp = self._call_route_api(origin_lat, origin_lon, dest_lat, dest_lon, azure_mode)
        routes = resp.get("routes", [])
        if not routes:
            logger.error(
                "No routes returned for '%s' -> '%s' (%s)",
                origin,
                dest_name,
                mode,
            )
            return None

        duration_seconds = routes[0]["summary"]["travelTimeInSeconds"]
        return TravelTime(
            destination_name=dest_name,
            destination_address=dest_address,
            mode=mode,
            duration_minutes=duration_seconds // 60,
            duration_text=f"{duration_seconds // 60} min",
        )

    def _geocode(self, address: str) -> tuple[float, float]:
        """Geocode an address to (lat, lon) using Azure Maps Search API.

        Isolated for testability — mock this method in tests.

        Args:
            address: Address string to geocode.

        Returns:
            (latitude, longitude) tuple.

        Raises:
            ValueError: If no results are returned for the address.
        """
        resp = requests.get(
            _AZURE_MAPS_SEARCH,
            params={
                "api-version": "1.0",
                "subscription-key": self._api_key,
                "query": address,
                "limit": 1,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            raise ValueError(f"No geocode results for address: {address!r}")
        position = results[0]["position"]
        return position["lat"], position["lon"]

    def _call_route_api(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str,
    ) -> dict:
        """Request route directions from Azure Maps Route API.

        Isolated for testability — mock this method in tests.

        Args:
            origin_lat: Origin latitude.
            origin_lon: Origin longitude.
            dest_lat: Destination latitude.
            dest_lon: Destination longitude.
            mode: Azure Maps travel mode string (car, pedestrian, bus).

        Returns:
            Parsed JSON response dict.
        """
        resp = requests.get(
            _AZURE_MAPS_ROUTE,
            params={
                "api-version": "1.0",
                "subscription-key": self._api_key,
                "query": f"{origin_lat},{origin_lon}:{dest_lat},{dest_lon}",
                "travelMode": mode,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _config_hash(self) -> str:
        """Hash the current destinations config for change detection."""
        config_str = json.dumps(self._destinations, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    def _config_matches(self, existing: dict) -> bool:
        """Check if the stored config hash matches the current destinations."""
        return existing.get("config_hash") == self._config_hash()

    @staticmethod
    def _load_previous_results(output_file: Path) -> dict | None:
        """Load previously saved distance results for idempotent re-runs.

        Args:
            output_file: Path to the distances.json file.

        Returns:
            Raw dict from the saved JSON, or None if not found.
        """
        if not output_file.exists():
            return None

        try:
            return json.loads(output_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read previous results from %s", output_file)
            return None

    def _save_results(self, output_file: Path, result: DistanceResult) -> None:
        """Save distance results to JSON.

        Args:
            output_file: Path to write the results.
            result: DistanceResult to serialize.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = result.model_dump()
        data["config_hash"] = self._config_hash()

        output_file.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Saved distance results to %s", output_file)
