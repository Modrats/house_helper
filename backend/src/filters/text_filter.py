"""TextFilter — filters houses by keywords in listing text.

Criteria keys:
    p1_keywords: list[str] — must-have, house must contain ALL (case-insensitive)
    p2_keywords: list[str] — nice-to-have, house must contain at least ONE (case-insensitive)
    excluded_keywords: list[str] — house must contain NONE of these (case-insensitive)
"""

from __future__ import annotations

from typing import Any

from ..interfaces.filter import IFilter
from ..models.house import FilterResult, House


class TextFilter(IFilter):
    """Filters houses based on keyword presence in listing text."""

    @property
    def name(self) -> str:
        return "text_filter"

    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> dict[str, FilterResult]:
        p1_keys = criteria.get("p1_keywords", [])
        p2_keys = criteria.get("p2_keywords", [])
        excluded_keys = criteria.get("excluded_keywords", [])

        results: dict[str, FilterResult] = {}
        for house in houses:
            lower_text = house.listing_text.lower()
            results[house.slug] = FilterResult(
                p1={kw: kw.lower() in lower_text for kw in p1_keys},
                p2={kw: kw.lower() in lower_text for kw in p2_keys},
                excluded={kw: kw.lower() in lower_text for kw in excluded_keys},
            )
        return results
