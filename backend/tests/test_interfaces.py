"""Unit tests for interfaces."""

from typing import Any, NamedTuple

import pytest

from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------


class IncompleteFilter(IFilter):
    """IFilter subclass missing the filter() method."""

    @property
    def name(self) -> str:
        return "incomplete"


class CompleteFilter(IFilter):
    """IFilter subclass implementing all required methods."""

    @property
    def name(self) -> str:
        return "complete"

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        return {h.slug: FilterResult() for h in houses}


class CustomNameFilter(IFilter):
    """IFilter subclass with a configurable name."""

    def __init__(self, filter_name: str) -> None:
        self._name = filter_name

    @property
    def name(self) -> str:
        return self._name

    def filter(self, houses: list[House], criteria: dict[str, Any]) -> dict[str, FilterResult]:
        return {h.slug: FilterResult() for h in houses}


class IFilterInstantiationErrorCase(NamedTuple):
    """Test case for IFilter subclasses that should raise TypeError on instantiation."""

    description: str
    factory: Any


IFILTER_INSTANTIATION_ERROR_CASES = [
    IFilterInstantiationErrorCase(
        description="IFilter cannot be instantiated directly without implementing abstract methods",
        factory=IFilter,
    ),
    IFilterInstantiationErrorCase(
        description="incomplete IFilter subclass missing filter() cannot be instantiated",
        factory=IncompleteFilter,
    ),
]


class IFilterCompleteCase(NamedTuple):
    """Test case for a valid complete IFilter implementation."""

    description: str
    filter_class: Any
    expected_name: str


IFILTER_COMPLETE_CASES = [
    IFilterCompleteCase(
        description="complete IFilter implementation can be instantiated and reports its name",
        filter_class=CompleteFilter,
        expected_name="complete",
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- IFilter complete implementation ---


@pytest.mark.parametrize("description, filter_class, expected_name", IFILTER_COMPLETE_CASES)
def test_ifilter_complete_implementation(
    description: str, filter_class: Any, expected_name: str
) -> None:
    """Complete IFilter subclass can be instantiated and reports its name."""
    # Arrange — (no setup needed)

    # Act
    f = filter_class()

    # Assert
    assert f.name == expected_name


# ===========================================================================
# Edge cases
# ===========================================================================

# --- IFilter subclass with custom name ---


def test_ifilter_subclass_with_custom_name() -> None:
    """IFilter subclass can define a custom dynamic name."""
    # Arrange
    custom_name = "my_special_filter"

    # Act
    f = CustomNameFilter(custom_name)

    # Assert
    assert f.name == custom_name


# --- CompleteFilter returns empty results for empty house list ---


def test_complete_filter_empty_house_list() -> None:
    """CompleteFilter returns empty results dict for empty house list."""
    # Arrange
    f = CompleteFilter()

    # Act
    results = f.filter([], {})

    # Assert
    assert results == {}


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- IFilter instantiation errors ---


@pytest.mark.parametrize("description, factory", IFILTER_INSTANTIATION_ERROR_CASES)
def test_ifilter_instantiation_error(description: str, factory: Any) -> None:
    """IFilter and incomplete subclasses cannot be instantiated."""
    # Arrange — (no setup needed)

    # Act & Assert
    with pytest.raises(TypeError):
        factory()  # type: ignore[abstract]
