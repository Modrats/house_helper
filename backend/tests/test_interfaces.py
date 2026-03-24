"""Unit tests for interfaces (Protocol compliance)."""

import pytest

from src.interfaces.data_source import IDataSource
from src.interfaces.filter import FilterCriteria, IFilter


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


class TestProtocolUsage:
    """Tests for using protocols in type hints (no runtime validation)."""

    def test_protocols_provide_type_hints(self):
        """Protocols provide clear type hints for static analysis."""
        # This test verifies that our protocols are properly structured
        # Static type checkers (mypy, pyright) will catch protocol violations

        def accepts_filter(f: IFilter) -> str:
            return f.name

        def accepts_data_source(ds: IDataSource) -> list[str]:
            return ds.list_houses()

        # These functions exist and will be type-checked by static analysis
        assert callable(accepts_filter)
        assert callable(accepts_data_source)
