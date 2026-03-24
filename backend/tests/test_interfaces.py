"""Unit tests for interfaces."""

from typing import Any

import pytest

from src.interfaces.data_source import IDataSource
from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House


class TestIFilterABC:
    """Tests for IFilter abstract base class enforcement."""

    def test_cannot_instantiate_directly(self):
        """IFilter cannot be instantiated without implementing abstract methods."""
        with pytest.raises(TypeError):
            IFilter()  # type: ignore[abstract]

    def test_incomplete_implementation_raises(self):
        """A subclass missing abstract methods cannot be instantiated."""

        class IncompleteFilter(IFilter):
            @property
            def name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteFilter()

    def test_complete_implementation_works(self):
        """A subclass implementing all abstract methods can be instantiated."""

        class CompleteFilter(IFilter):
            @property
            def name(self) -> str:
                return "complete"

            def filter(
                self, houses: list[House], criteria: dict[str, Any]
            ) -> dict[str, FilterResult]:
                return {h.slug: FilterResult() for h in houses}

        f = CompleteFilter()
        assert f.name == "complete"


class TestInterfaceTypeHints:
    """Tests for using interfaces in type hints."""

    def test_type_hints_work(self):
        """Interfaces provide clear type hints."""

        def accepts_filter(f: IFilter) -> str:
            return f.name

        def accepts_data_source(ds: IDataSource) -> list:
            return ds.get_all_houses()

        assert callable(accepts_filter)
        assert callable(accepts_data_source)
