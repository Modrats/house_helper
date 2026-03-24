"""Unit tests for TextFilter."""

from typing import NamedTuple

import pytest

from src.filters.text_filter import TextFilter
from src.models.house import FilterResult
from tests.conftest import make_house


# ---------------------------------------------------------------------------
# TextFilter — single-house evaluation
# ---------------------------------------------------------------------------


class TextFilterCase(NamedTuple):
    """Test case for TextFilter.filter() single-house output."""

    description: str
    listing_text: str
    criteria: dict
    expected_passed: bool


TEXT_FILTER_CASES = [
    TextFilterCase(
        description="no criteria — house always passes",
        listing_text="nice place near the park",
        criteria={},
        expected_passed=True,
    ),
    TextFilterCase(
        description="p1 all keywords present — passes",
        listing_text="garden balcony parking included",
        criteria={"p1_keywords": ["garden", "balcony"]},
        expected_passed=True,
    ),
    TextFilterCase(
        description="p1 one keyword missing — fails",
        listing_text="garden only no balcony here",
        criteria={"p1_keywords": ["garden", "balcony", "pool"]},
        expected_passed=False,
    ),
    TextFilterCase(
        description="p2 one keyword present — passes",
        listing_text="large kitchen with storage",
        criteria={"p2_keywords": ["kitchen", "garage"]},
        expected_passed=True,
    ),
    TextFilterCase(
        description="p2 no keywords present — fails",
        listing_text="tiny studio no amenities",
        criteria={"p2_keywords": ["garden", "garage"]},
        expected_passed=False,
    ),
    TextFilterCase(
        description="excluded keyword present — fails",
        listing_text="nice home but needs renovation",
        criteria={"excluded_keywords": ["renovation"]},
        expected_passed=False,
    ),
    TextFilterCase(
        description="excluded keyword absent — passes",
        listing_text="move-in ready bright apartment",
        criteria={"excluded_keywords": ["renovation"]},
        expected_passed=True,
    ),
    TextFilterCase(
        description="case-insensitive — uppercase criterion matched against lowercase text",
        listing_text="garden and balcony included",
        criteria={"p1_keywords": ["GARDEN", "BALCONY"]},
        expected_passed=True,
    ),
    TextFilterCase(
        description="empty listing text with non-empty p1 — fails",
        listing_text="",
        criteria={"p1_keywords": ["garden"]},
        expected_passed=False,
    ),
]


@pytest.mark.parametrize(
    "description, listing_text, criteria, expected_passed",
    TEXT_FILTER_CASES,
)
def test_text_filter_single_house(
    description: str,
    listing_text: str,
    criteria: dict,
    expected_passed: bool,
) -> None:
    house = make_house(slug="test-house", listing_text=listing_text)
    result = TextFilter().filter([house], criteria)
    assert result["test-house"].passed == expected_passed


# ---------------------------------------------------------------------------
# TextFilter — multiple houses evaluated independently
# ---------------------------------------------------------------------------


class TextFilterMultiHouseCase(NamedTuple):
    """Test case verifying multiple houses are evaluated independently."""

    description: str
    houses_texts: list
    criteria: dict
    expected_results: dict


TEXT_FILTER_MULTI_CASES = [
    TextFilterMultiHouseCase(
        description="multiple houses — each evaluated independently without cross-contamination",
        houses_texts=[
            ("house-a", "garden and balcony included"),
            ("house-b", "no outdoor space at all"),
        ],
        criteria={"p1_keywords": ["garden"]},
        expected_results={"house-a": True, "house-b": False},
    ),
]


@pytest.mark.parametrize(
    "description, houses_texts, criteria, expected_results",
    TEXT_FILTER_MULTI_CASES,
)
def test_text_filter_multiple_houses(
    description: str,
    houses_texts: list,
    criteria: dict,
    expected_results: dict,
) -> None:
    houses = [make_house(slug=slug, listing_text=text) for slug, text in houses_texts]
    results = TextFilter().filter(houses, criteria)
    for slug, expected_passed in expected_results.items():
        assert results[slug].passed == expected_passed
