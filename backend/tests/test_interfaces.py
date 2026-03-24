"""Unit tests for interfaces (Protocol compliance)."""

import pytest

from src.interfaces.filter import FilterCriteria, IFilter
from src.models.house import House


class TestFilterCriteria:
    """Tests for FilterCriteria model."""

    def test_empty_criteria(self):
        """Criteria can be created empty."""
        criteria = FilterCriteria()
        assert criteria.must_have_keywords == []
        assert criteria.min_bedrooms is None
        assert criteria.max_price is None

    def test_text_criteria(self):
        """Text-based criteria work correctly."""
        criteria = FilterCriteria(
            must_have_keywords=["garden", "renovated"],
            must_not_have_keywords=["shared", "studio"],
        )
        assert "garden" in criteria.must_have_keywords
        assert "shared" in criteria.must_not_have_keywords

    def test_room_criteria(self):
        """Room-based criteria work correctly."""
        criteria = FilterCriteria(
            min_bedrooms=2,
            required_room_types=["kitchen", "bathroom"],
        )
        assert criteria.min_bedrooms == 2
        assert "kitchen" in criteria.required_room_types

    def test_location_criteria(self):
        """Location-based criteria work correctly."""
        criteria = FilterCriteria(
            max_commute_minutes=30,
            commute_destination="Amsterdam Central",
        )
        assert criteria.max_commute_minutes == 30
        assert criteria.commute_destination == "Amsterdam Central"

    def test_price_criteria(self):
        """Price criteria work correctly."""
        criteria = FilterCriteria(
            min_price=200000,
            max_price=500000,
        )
        assert criteria.min_price == 200000
        assert criteria.max_price == 500000

    def test_criteria_allows_extra_fields(self):
        """Criteria allows extension with custom fields."""
        criteria = FilterCriteria(
            custom_field="custom_value",
            another_custom=123,
        )
        assert criteria.custom_field == "custom_value"
        assert criteria.another_custom == 123

    def test_price_non_negative(self):
        """Price bounds must be non-negative."""
        with pytest.raises(ValueError):
            FilterCriteria(max_price=-100)
        with pytest.raises(ValueError):
            FilterCriteria(min_price=-1)


class TestIFilterProtocol:
    """Tests to verify IFilter Protocol structure."""

    def test_protocol_is_runtime_checkable(self):
        """IFilter is runtime_checkable for isinstance checks."""

        # Create a minimal implementation
        class MockFilter:
            @property
            def name(self) -> str:
                return "mock_filter"

            def filter(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
                return houses

            async def filter_async(
                self, houses: list[House], criteria: FilterCriteria
            ) -> list[House]:
                return houses

        mock = MockFilter()
        assert isinstance(mock, IFilter)

    def test_non_conforming_class_fails_check(self):
        """Classes without required methods don't match Protocol."""

        class NotAFilter:
            pass

        assert not isinstance(NotAFilter(), IFilter)

    def test_partial_implementation_fails_check(self):
        """Partial implementations don't match Protocol."""

        class PartialFilter:
            def filter(self, houses: list[House], criteria: FilterCriteria) -> list[House]:
                return houses

            # Missing filter_async and name

        assert not isinstance(PartialFilter(), IFilter)
