"""Unit tests for the filter pipeline runner."""

from typing import Any

import pytest

from src.models.house import House, HouseMetadata
from src.runners.run_pipeline import FilterPipeline


class PassAllFilter:
    """Filter that passes all houses (for testing)."""

    @property
    def name(self) -> str:
        return "pass_all"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return houses

    async def filter_async(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return self.filter(houses, criteria)


class RejectAllFilter:
    """Filter that rejects all houses (for testing)."""

    @property
    def name(self) -> str:
        return "reject_all"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return []

    async def filter_async(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return []


class PriceFilter:
    """Filter houses by max price (for testing)."""

    @property
    def name(self) -> str:
        return "price_filter"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        max_price = criteria.get("max_price")
        if max_price is None:
            return houses
        return [h for h in houses if h.metadata.price is not None and h.metadata.price <= max_price]

    async def filter_async(self, houses: list[House], criteria: dict[str, Any]) -> list[House]:
        return self.filter(houses, criteria)


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


@pytest.mark.asyncio
class TestFilterPipelineAsync:
    """Async tests for FilterPipeline."""

    @pytest.fixture
    def sample_houses(self) -> list[House]:
        """Create sample houses for testing."""
        return [
            House(slug="house-1", metadata=HouseMetadata(price=300000)),
            House(slug="house-2", metadata=HouseMetadata(price=450000)),
        ]

    async def test_async_pipeline(self, sample_houses):
        """Async pipeline runs correctly."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        result = await pipeline.run_async(sample_houses, {})
        assert len(result) == 2
