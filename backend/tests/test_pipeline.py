"""Unit tests for the filter pipeline runner."""

import pytest

from src.interfaces.filter import FilterCriteria
from src.models.house import House, HouseMetadata
from src.runners.run_pipeline import FilterPipeline, PipelineConfig, PipelineResult


class PassAllFilter:
    """Filter that passes all houses (for testing)."""

    @property
    def name(self) -> str:
        return "pass_all"

    def filter(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
        return [h.with_filter_result(self.name, True) for h in houses]

    async def filter_async(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
        return self.filter(houses, criteria)


class RejectAllFilter:
    """Filter that rejects all houses (for testing)."""

    @property
    def name(self) -> str:
        return "reject_all"

    def filter(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
        return []

    async def filter_async(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
        return []


class PriceFilter:
    """Filter houses by max price (for testing)."""

    @property
    def name(self) -> str:
        return "price_filter"

    def filter(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
        if criteria.max_price is None:
            return houses
        result = []
        for h in houses:
            if h.metadata.price is not None and h.metadata.price <= criteria.max_price:
                result.append(h.with_filter_result(self.name, True))
        return result

    async def filter_async(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
        return self.filter(houses, criteria)


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = PipelineConfig()
        assert config.mode == "async"
        assert config.max_workers == 4
        assert config.fail_fast is False
        assert config.continue_on_error is True


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_pass_rate_calculation(self):
        """Pass rate is calculated correctly."""
        result = PipelineResult(
            houses=[House(slug="a"), House(slug="b")],
            input_count=10,
            output_count=2,
            filters_applied=["test"],
        )
        assert result.pass_rate == 20.0

    def test_pass_rate_zero_input(self):
        """Pass rate handles zero input."""
        result = PipelineResult(
            houses=[],
            input_count=0,
            output_count=0,
            filters_applied=[],
        )
        assert result.pass_rate == 0.0


class TestFilterPipeline:
    """Tests for FilterPipeline."""

    @pytest.fixture
    def sample_houses(self) -> list[House]:
        """Create sample houses for testing."""
        return [
            House(
                slug="house-1",
                metadata=HouseMetadata(price=300000),
            ),
            House(
                slug="house-2",
                metadata=HouseMetadata(price=450000),
            ),
            House(
                slug="house-3",
                metadata=HouseMetadata(price=600000),
            ),
        ]

    def test_empty_pipeline(self, sample_houses):
        """Pipeline with no filters passes all houses."""
        pipeline = FilterPipeline()
        result = pipeline.run(sample_houses, FilterCriteria())
        assert result.output_count == 3
        assert result.input_count == 3

    def test_add_and_run_filter(self, sample_houses):
        """Filters are applied correctly."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        result = pipeline.run(sample_houses, FilterCriteria())
        assert result.output_count == 3
        assert "pass_all" in result.filters_applied

    def test_chained_filters(self, sample_houses):
        """Multiple filters chain correctly."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        pipeline.add_filter(PriceFilter())

        criteria = FilterCriteria(max_price=400000)
        result = pipeline.run(sample_houses, criteria)

        assert result.output_count == 1  # Only house-1 at 300k
        assert result.input_count == 3
        assert len(result.filters_applied) == 2

    def test_reject_all_filter(self, sample_houses):
        """RejectAll filter excludes all houses."""
        pipeline = FilterPipeline()
        pipeline.add_filter(RejectAllFilter())
        result = pipeline.run(sample_houses, FilterCriteria())
        assert result.output_count == 0

    def test_fail_fast_mode(self, sample_houses):
        """Fail-fast stops on first empty result."""
        config = PipelineConfig(fail_fast=True)
        pipeline = FilterPipeline(config)
        pipeline.add_filter(RejectAllFilter())
        pipeline.add_filter(PassAllFilter())  # Should not run

        result = pipeline.run(sample_houses, FilterCriteria())
        assert result.output_count == 0
        assert len(result.filters_applied) == 1  # Only reject_all ran

    def test_method_chaining(self):
        """Pipeline methods support chaining."""
        pipeline = (
            FilterPipeline()
            .add_filter(PassAllFilter())
            .add_filter(PriceFilter())
        )
        assert len(pipeline.filters) == 2

    def test_remove_filter(self):
        """Filters can be removed by name."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        pipeline.add_filter(PriceFilter())
        pipeline.remove_filter("price_filter")
        assert len(pipeline.filters) == 1
        assert pipeline.filters[0].name == "pass_all"

    def test_clear_filters(self):
        """All filters can be cleared."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        pipeline.add_filter(PriceFilter())
        pipeline.clear_filters()
        assert len(pipeline.filters) == 0

    def test_filter_stats(self, sample_houses):
        """Filter statistics are tracked."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PriceFilter())

        criteria = FilterCriteria(max_price=400000)
        result = pipeline.run(sample_houses, criteria)

        stats = result.filter_stats["price_filter"]
        assert stats["input"] == 3
        assert stats["output"] == 1
        assert stats["excluded"] == 2


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
        result = await pipeline.run_async(sample_houses, FilterCriteria())
        assert result.output_count == 2

    async def test_parallel_house_processing(self, sample_houses):
        """Parallel house processing works."""
        pipeline = FilterPipeline()
        pipeline.add_filter(PassAllFilter())
        result = await pipeline.run_parallel_houses(sample_houses, FilterCriteria())
        assert result.output_count == 2
