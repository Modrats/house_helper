"""DistanceFilter — filters houses by commute time via Azure Maps.

Uses the Azure Maps Search API to geocode the house address and then the
Routing API to calculate drive time to each configured destination.

Criteria keys (under ``distance_filter`` in criteria.yaml):
    max_commute_minutes: int  — maximum acceptable one-way drive time in minutes
    destinations: list[str]  — destination addresses / place names to route to

Graceful degradation:
    - Houses without address metadata pass through without penalty.
    - If geocoding fails for a house or destination the route is skipped.
    - If AZURE_MAPS_KEY is not set the filter should not be added to the pipeline
      (handled in run.py).
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ..interfaces.filter import IFilter
from ..models.house import FilterResult, House

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://atlas.microsoft.com/search/address/json"
_ROUTE_URL = "https://atlas.microsoft.com/route/directions/json"
_MAPS_API_VERSION = "1.0"
_REQUEST_TIMEOUT = 10


class DistanceFilter(IFilter):
    """Filters houses by commute time using Azure Maps Routing.

    For each house, geocodes the house's postal code / city via the
    Azure Maps Search API and then queries the Routing API for each
    configured destination.  Commute time is compared against
    ``max_commute_minutes`` from the criteria.

    Args:
        api_key: Azure Maps subscription key.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "distance_filter"

    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> dict[str, FilterResult]:
        max_minutes: int = criteria.get("max_commute_minutes", 60)
        # destinations can be a flat list of address strings
        # or a list of dicts with {name, address, modes} (upstream schema)
        raw_destinations: list = criteria.get("destinations", [])

        if not raw_destinations:
            logger.info("No destinations configured — distance filter is a no-op")
            return {h.slug: FilterResult() for h in houses}

        # Normalise to list of (label, address) tuples
        destinations: list[tuple[str, str]] = []
        for d in raw_destinations:
            if isinstance(d, str):
                destinations.append((d, d))
            else:
                destinations.append((d.get("name", d["address"]), d["address"]))

        results: dict[str, FilterResult] = {}
        for house in houses:
            results[house.slug] = self._evaluate(house, destinations, max_minutes)
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _evaluate(
        self,
        house: House,
        destinations: list[tuple[str, str]],
        max_minutes: int,
    ) -> FilterResult:
        address = self._house_address(house)
        if not address:
            logger.info("House '%s' has no address metadata — distance check skipped", house.slug)
            return FilterResult()

        house_coords = self._geocode(address)
        if not house_coords:
            logger.warning(
                "Could not geocode address for '%s': %s — distance check skipped",
                house.slug,
                address,
            )
            return FilterResult()

        p1: dict[str, bool] = {}
        for label, dest_address in destinations:
            dest_coords = self._geocode(dest_address)
            if not dest_coords:
                logger.warning("Could not geocode destination '%s' — skipping", dest_address)
                continue

            minutes = self._route_minutes(house_coords, dest_coords)
            key = f"commute_{label[:40].replace(' ', '_')}"
            passed = minutes is not None and minutes <= max_minutes
            p1[key] = passed

            if minutes is not None:
                logger.info(
                    "'%s' → '%s': %d min (limit %d) — %s",
                    house.slug,
                    label,
                    minutes,
                    max_minutes,
                    "✓" if passed else "✗",
                )

        return FilterResult(p1=p1)

    @staticmethod
    def _house_address(house: House) -> str | None:
        """Build a geocodable address string from house metadata."""
        m = house.metadata
        if m.postal_code and m.city:
            return f"{m.postal_code} {m.city}, Netherlands"
        if m.address and m.city:
            return f"{m.address}, {m.city}, Netherlands"
        if m.city:
            return f"{m.city}, Netherlands"
        return None

    def _geocode(self, address: str) -> tuple[float, float] | None:
        """Return (lat, lon) for the given address, or None on failure."""
        try:
            resp = requests.get(
                _SEARCH_URL,
                params={
                    "api-version": _MAPS_API_VERSION,
                    "subscription-key": self._api_key,
                    "query": address,
                    "limit": 1,
                    "countrySet": "NL",
                },
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            hits = resp.json().get("results", [])
            if not hits:
                return None
            pos = hits[0]["position"]
            return float(pos["lat"]), float(pos["lon"])
        except Exception as exc:
            logger.warning("Geocode failed for '%s': %s", address, exc)
            return None

    def _route_minutes(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
    ) -> int | None:
        """Return drive time in minutes between two coordinate pairs, or None."""
        try:
            query = f"{origin[0]},{origin[1]}:{dest[0]},{dest[1]}"
            resp = requests.get(
                _ROUTE_URL,
                params={
                    "api-version": _MAPS_API_VERSION,
                    "subscription-key": self._api_key,
                    "query": query,
                    "travelMode": "car",
                },
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            legs = resp.json()["routes"][0]["legs"]
            total_seconds: int = sum(leg["summary"]["travelTimeInSeconds"] for leg in legs)
            return total_seconds // 60
        except Exception as exc:
            logger.warning("Routing request failed: %s", exc)
            return None
