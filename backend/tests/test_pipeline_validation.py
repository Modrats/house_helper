"""Tests for FilterPipeline basic functionality.

Tests pipeline operations with proper filter implementations
to ensure normal usage works correctly.
"""

from typing import Any, NamedTuple

import pytest

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


class FilterA(IFilter):
    """Named filter for order verification."""

    @property
    def name(self) -> str:
        return "filter_a"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        return {h.slug: FilterResult() for h in houses}


class FilterB(IFilter):
    """Named filter for order verification."""

    @property
    def name(self) -> str:
        return "filter_b"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        return {h.slug: FilterResult() for h in houses}


# ---------------------------------------------------------------------------
# add_filter returns self
# ---------------------------------------------------------------------------


class AddFilterChainCase(NamedTuple):
    """Test case for add_filter chaining behaviour."""

    description: str
    expected_filter_count: int


ADD_FILTER_CHAIN_CASES = [
    AddFilterChainCase(
        description="add_filter returns the pipeline instance enabling method chaining",
        expected_filter_count=1,
    ),
]


@pytest.mark.parametrize("description, expected_filter_count", ADD_FILTER_CHAIN_CASES)
def test_add_filter_returns_self_for_chaining(
    description: str, expected_filter_count: int
) -> None:
    pipeline = FilterPipeline()
    result = pipeline.add_filter(SimpleFilter())
    assert result is pipeline
    assert len(pipeline.filters) == expected_filter_count


# ---------------------------------------------------------------------------
# Filter ordering
# ---------------------------------------------------------------------------


class FilterOrderCase(NamedTuple):
    """Test case for filter storage order."""

    description: str
    filter_1: IFilter
    filter_2: IFilter
    expected_name_0: str
    expected_name_1: str
    expected_count: int


FILTER_ORDER_CASES = [
    FilterOrderCase(
        description="multiple filters are stored in the order they were added",
        filter_1=SimpleFilter(),
        filter_2=KeywordFilter(),
        expected_name_0="simple_filter",
        expected_name_1="keyword_filter",
        expected_count=2,
    ),
    FilterOrderCase(
        description="filters with distinguishable names are stored in insertion order",
        filter_1=FilterA(),
        filter_2=FilterB(),
        expected_name_0="filter_a",
        expected_name_1="filter_b",
        expected_count=2,
    ),
]


@pytest.mark.parametrize(
    "description, filter_1, filter_2, expected_name_0, expected_name_1, expected_count",
    FILTER_ORDER_CASES,
)
def test_filters_stored_in_order(
    description: str,
    filter_1: IFilter,
    filter_2: IFilter,
    expected_name_0: str,
    expected_name_1: str,
    expected_count: int,
) -> None:
    pipeline = FilterPipeline()
    pipeline.add_filter(filter_1).add_filter(filter_2)
    assert len(pipeline.filters) == expected_count
    assert pipeline.filters[0].name == expected_name_0
    assert pipeline.filters[1].name == expected_name_1


# ---------------------------------------------------------------------------
# Empty pipeline
# ---------------------------------------------------------------------------


class EmptyPipelineCase(NamedTuple):
    """Test case for a freshly created pipeline."""

    description: str
    expected_filter_count: int


EMPTY_PIPELINE_CASES = [
    EmptyPipelineCase(
        description="new pipeline starts with zero filters",
        expected_filter_count=0,
    ),
]


@pytest.mark.parametrize("description, expected_filter_count", EMPTY_PIPELINE_CASES)
def test_pipeline_starts_empty(description: str, expected_filter_count: int) -> None:
    pipeline = FilterPipeline()
    assert len(pipeline.filters) == expected_filter_count

