"""Unit tests for the filter pipeline runner."""

from typing import Any, NamedTuple

import pytest

from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House, HouseMetadata
from src.runners.run_pipeline import FilterPipeline

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class PassAllFilter(IFilter):
    """Filter that passes all houses (for testing)."""

    @property
    def name(self) -> str:
        return "pass_all"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        return {h.slug: FilterResult() for h in houses}


class RejectAllFilter(IFilter):
    """Filter that rejects all houses (for testing)."""

    @property
    def name(self) -> str:
        return "reject_all"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        return {h.slug: FilterResult(p1={"required": False}) for h in houses}


class PriceFilter(IFilter):
    """Filter houses by max price (for testing)."""

    @property
    def name(self) -> str:
        return "price_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        max_price = criteria.get("max_price")
        results: dict[str, FilterResult] = {}
        for h in houses:
            if max_price is None:
                results[h.slug] = FilterResult()
            else:
                passed = h.metadata.price is not None and h.metadata.price <= max_price
                results[h.slug] = FilterResult(p1={"max_price": passed})
        return results


class RaisingFilter(IFilter):
    """Filter that raises an exception (for testing error propagation)."""

    @property
    def name(self) -> str:
        return "raising_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        raise RuntimeError("Filter failure")


SAMPLE_HOUSES = [
    House(slug="house-1", metadata=HouseMetadata(price=300000)),
    House(slug="house-2", metadata=HouseMetadata(price=450000)),
    House(slug="house-3", metadata=HouseMetadata(price=600000)),
]


class PipelineRunCase(NamedTuple):
    """Test case for FilterPipeline.run() output size."""

    description: str
    filters: list
    houses: list
    criteria: dict
    expected_count: int


PIPELINE_RUN_CASES = [
    PipelineRunCase(
        description="empty pipeline with no filters passes all houses",
        filters=[],
        houses=SAMPLE_HOUSES,
        criteria={},
        expected_count=3,
    ),
    PipelineRunCase(
        description="pass-all filter passes every house unchanged",
        filters=[PassAllFilter()],
        houses=SAMPLE_HOUSES,
        criteria={},
        expected_count=3,
    ),
    PipelineRunCase(
        description="chained pass-all and price filter with max 400k keeps only house-1",
        filters=[PassAllFilter(), PriceFilter()],
        houses=SAMPLE_HOUSES,
        criteria={"max_price": 400000},
        expected_count=1,
    ),
    PipelineRunCase(
        description="reject-all filter excludes every house",
        filters=[RejectAllFilter()],
        houses=SAMPLE_HOUSES,
        criteria={},
        expected_count=0,
    ),
]


class PipelineChainCase(NamedTuple):
    """Test case for FilterPipeline method chaining."""

    description: str
    expected_filter_count: int


PIPELINE_CHAIN_CASES = [
    PipelineChainCase(
        description="chained add_filter calls accumulate filters in the pipeline",
        expected_filter_count=2,
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- Pipeline run ---


@pytest.mark.parametrize(
    "description, filters, houses, criteria, expected_count", PIPELINE_RUN_CASES
)
def test_pipeline_run(
    description: str,
    filters: list,
    houses: list,
    criteria: dict,
    expected_count: int,
) -> None:
    """FilterPipeline.run applies filters and returns passing houses."""
    # Arrange
    pipeline = FilterPipeline()
    for f in filters:
        pipeline.add_filter(f)

    # Act
    result = pipeline.run(houses, criteria)

    # Assert
    assert len(result) == expected_count


# --- Method chaining ---


@pytest.mark.parametrize("description, expected_filter_count", PIPELINE_CHAIN_CASES)
def test_pipeline_method_chaining(description: str, expected_filter_count: int) -> None:
    """FilterPipeline.add_filter supports method chaining."""
    # Arrange — (no setup needed)

    # Act
    pipeline = FilterPipeline().add_filter(PassAllFilter()).add_filter(PriceFilter())

    # Assert
    assert len(pipeline.filters) == expected_filter_count


# ===========================================================================
# Edge cases
# ===========================================================================

# --- Pipeline with empty house list ---


def test_pipeline_run_empty_house_list() -> None:
    """Pipeline run with empty house list returns empty list."""
    # Arrange
    pipeline = FilterPipeline()
    pipeline.add_filter(PassAllFilter())

    # Act
    result = pipeline.run([], {})

    # Assert
    assert result == []


# --- Pipeline with single house that passes all filters ---


def test_pipeline_single_house_passes_all() -> None:
    """Pipeline with single house that passes all filters returns that house."""
    # Arrange
    pipeline = FilterPipeline()
    pipeline.add_filter(PassAllFilter())
    pipeline.add_filter(PriceFilter())
    houses = [House(slug="cheap-house", metadata=HouseMetadata(price=100000))]

    # Act
    result = pipeline.run(houses, {"max_price": 500000})

    # Assert
    assert len(result) == 1
    assert result[0].slug == "cheap-house"


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- Filter that raises ---


def test_pipeline_filter_raises_propagates() -> None:
    """A filter that raises an exception propagates it to the caller."""
    # Arrange
    pipeline = FilterPipeline()
    pipeline.add_filter(RaisingFilter())

    # Act & Assert
    with pytest.raises(RuntimeError, match="Filter failure"):
        pipeline.run(SAMPLE_HOUSES, {})
