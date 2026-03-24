"""Unit tests for interfaces (Protocol compliance)."""

from src.interfaces.data_source import IDataSource
from src.interfaces.filter import IFilter


class TestProtocolUsage:
    """Tests for using protocols in type hints (no runtime validation)."""

    def test_protocols_provide_type_hints(self):
        """Protocols provide clear type hints for static analysis."""

        def accepts_filter(f: IFilter) -> str:
            return f.name

        def accepts_data_source(ds: IDataSource) -> list:
            return ds.get_all_houses()

        assert callable(accepts_filter)
        assert callable(accepts_data_source)
