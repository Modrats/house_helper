"""Shared test helpers for the backend test suite."""

from typing import Any

from src.interfaces.filter import IFilter
from src.models.house import FilterResult, House, HouseMetadata

# ---------------------------------------------------------------------------
# Shared filter doubles
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


# ---------------------------------------------------------------------------
# House factory
# ---------------------------------------------------------------------------


def make_house(slug: str, listing_text: str = "", price: int | None = None, **kwargs) -> House:
    """Construct a House with sensible defaults. Accepts extra House fields via kwargs."""
    meta_kwargs: dict[str, Any] = {}
    if price is not None:
        meta_kwargs["price"] = price
    return House(
        slug=slug,
        listing_text=listing_text,
        metadata=HouseMetadata(**meta_kwargs),
        **kwargs,
    )
