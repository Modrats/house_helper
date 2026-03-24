"""Unit tests for interfaces."""

from typing import Any, NamedTuple

import pytest

from src.interfaces.data_source import IDataSource
from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House


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

    def filter(
        self, houses: list[House], criteria: dict[str, Any]
    ) -> dict[str, FilterResult]:
        return {h.slug: FilterResult() for h in houses}


# ---------------------------------------------------------------------------
# IFilter ABC — instantiation errors
# ---------------------------------------------------------------------------


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


@pytest.mark.parametrize("description, factory", IFILTER_INSTANTIATION_ERROR_CASES)
def test_ifilter_instantiation_error(description: str, factory: Any) -> None:
    with pytest.raises(TypeError):
        factory()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# IFilter ABC — complete implementation
# ---------------------------------------------------------------------------


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


@pytest.mark.parametrize("description, filter_class, expected_name", IFILTER_COMPLETE_CASES)
def test_ifilter_complete_implementation(
    description: str, filter_class: Any, expected_name: str
) -> None:
    f = filter_class()
    assert f.name == expected_name


# ---------------------------------------------------------------------------
# Interface type hints
# ---------------------------------------------------------------------------


class TypeHintsCase(NamedTuple):
    """Test case for interfaces as type hint parameters."""

    description: str
    expected_callable_count: int


TYPE_HINTS_CASES = [
    TypeHintsCase(
        description="interfaces can be used as type hints for function parameters",
        expected_callable_count=2,
    ),
]


@pytest.mark.parametrize("description, expected_callable_count", TYPE_HINTS_CASES)
def test_type_hints_work(description: str, expected_callable_count: int) -> None:
    def accepts_filter(f: IFilter) -> str:
        return f.name

    def accepts_data_source(ds: IDataSource) -> list:
        return ds.get_all_houses()

    callables = [accepts_filter, accepts_data_source]
    assert len(callables) == expected_callable_count
    assert all(callable(c) for c in callables)

