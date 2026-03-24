"""Tests for FilterPipeline basic functionality.

Tests pipeline operations with proper filter implementations
to ensure normal usage works correctly. Static type checking
(mypy/pyright) handles interface validation.
"""

from typing import Any

from src.models.house import House
from src.runners.run_pipeline import FilterPipeline


class SimpleFilter:
    """A simple filter for testing."""

    @property
    def name(self) -> str:
        return "simple_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        """Return houses with more than 2 bedrooms."""
        return [h for h in houses if h.bedroom_count > 2]

    async def filter_async(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return self.filter(houses, criteria)


class KeywordFilter:
    """Filter houses by keywords in listing text."""

    @property
    def name(self) -> str:
        return "keyword_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        """Filter by required keywords."""
        must_have = criteria.get("must_have_keywords", [])
        if not must_have:
            return houses

        results = []
        for house in houses:
            listing_text = (house.listing_text or "").lower()
            if all(kw.lower() in listing_text for kw in must_have):
                results.append(house)
        return results

    async def filter_async(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return self.filter(houses, criteria)


class TestFilterPipeline:
    """Tests for FilterPipeline functionality."""

    def test_add_filter_returns_self_for_chaining(self):
        """add_filter() returns self to enable method chaining."""
        pipeline = FilterPipeline()
        result = pipeline.add_filter(SimpleFilter())

        assert result is pipeline
        assert len(pipeline.filters) == 1

    def test_multiple_filters_can_be_added(self):
        """Multiple filters can be chained in order."""
        pipeline = FilterPipeline()
        filter1 = SimpleFilter()
        filter2 = KeywordFilter()

        pipeline.add_filter(filter1).add_filter(filter2)

        assert len(pipeline.filters) == 2
        assert pipeline.filters[0] is filter1
        assert pipeline.filters[1] is filter2

    def test_filters_are_stored_in_order(self):
        """Filters are stored in the order they were added."""
        pipeline = FilterPipeline()

        # Add filters with distinguishable names
        class FilterA:
            name = "filter_a"

            def filter(self, houses, criteria):
                return houses

            async def filter_async(self, houses, criteria):
                return houses

        class FilterB:
            name = "filter_b"

            def filter(self, houses, criteria):
                return houses

            async def filter_async(self, houses, criteria):
                return houses

        pipeline.add_filter(FilterA()).add_filter(FilterB())

        assert pipeline.filters[0].name == "filter_a"
        assert pipeline.filters[1].name == "filter_b"

    def test_pipeline_starts_empty(self):
        """New pipeline starts with no filters."""
        pipeline = FilterPipeline()
        assert len(pipeline.filters) == 0
