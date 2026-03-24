"""Tests for FilterPipeline basic functionality.

Tests pipeline operations with proper filter implementations
to ensure normal usage works correctly.
"""

from typing import Any

from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House
from src.runners.run_pipeline import FilterPipeline


class SimpleFilter(IFilter):
    """A simple filter for testing."""

    @property
    def name(self) -> str:
        return "simple_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        """Return pass for houses with more than 2 bedrooms."""
        return {h.slug: FilterResult(p1={"bedrooms_gt_2": h.bedroom_count > 2}) for h in houses}


class KeywordFilter(IFilter):
    """Filter houses by keywords in listing text."""

    @property
    def name(self) -> str:
        return "keyword_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        """Filter by required keywords."""
        must_have = criteria.get("must_have_keywords", [])
        if not must_have:
            return {h.slug: FilterResult() for h in houses}

        results: dict[str, FilterResult] = {}
        for house in houses:
            listing_text = (house.listing_text or "").lower()
            results[house.slug] = FilterResult(
                p1={kw: kw.lower() in listing_text for kw in must_have}
            )
        return results


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
        class FilterA(IFilter):
            @property
            def name(self):
                return "filter_a"

            def filter(self, houses, criteria):
                return houses

        class FilterB(IFilter):
            @property
            def name(self):
                return "filter_b"

            def filter(self, houses, criteria):
                return houses

        pipeline.add_filter(FilterA()).add_filter(FilterB())

        assert pipeline.filters[0].name == "filter_a"
        assert pipeline.filters[1].name == "filter_b"

    def test_pipeline_starts_empty(self):
        """New pipeline starts with no filters."""
        pipeline = FilterPipeline()
        assert len(pipeline.filters) == 0
