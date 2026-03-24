"""Unit tests for the filter pipeline runner."""

from typing import Any

import pytest

from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House, HouseMetadata
from src.runners.run_pipeline import FilterPipeline


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


class TestFilterPipeline:
    """Tests for FilterPipeline."""

    @pytest.fixture
    def sample_houses(self) -> list[House]:
        """Create sample houses for testing."""
        return [
            House(slug="house-1", metadata=HouseMetadata(price=300000)),
            House(slug="house-2", metadata=HouseMetadata(price=450000)),
            House(slug="house-3", metadata=HouseMetadata(price=600000)),
        ]

    def test_empty_pipeline(self, sample_houses):
        """Pipeline with no filters passes all houses."""
        pipeline = FilterPipeline()
        result = pipeline.run(sample_houses, {})
        assert len(result) == 3

    def test_add_and_run_filter(self, sample_houses):
        """Filters are applied correctly."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        result = pipeline.run(sample_houses, {})
        assert len(result) == 3

    def test_chained_filters(self, sample_houses):
        """Multiple filters chain correctly."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        pipeline.add_filter(PriceFilter())

        result = pipeline.run(sample_houses, {"max_price": 400000})
        assert len(result) == 1  # Only house-1 at 300k

    def test_reject_all_filter(self, sample_houses):
        """RejectAll filter excludes all houses."""
        pipeline = FilterPipeline()
        pipeline.add_filter(RejectAllFilter())
        result = pipeline.run(sample_houses, {})
        assert len(result) == 0

    def test_method_chaining(self):
        """Pipeline methods support chaining."""
        pipeline = FilterPipeline().add_filter(PassAllFilter()).add_filter(PriceFilter())
        assert len(pipeline.filters) == 2
