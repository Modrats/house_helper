"""Unit tests for TextFilter."""

from typing import NamedTuple

import pytest

from src.filters.text_filter import TextFilter
from tests.conftest import make_house

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
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


# ===========================================================================
# Happy path
# ===========================================================================

# --- TextFilter single-house ---


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
    """TextFilter evaluates a single house against criteria."""
    # Arrange
    house = make_house(slug="test-house", listing_text=listing_text)
    text_filter = TextFilter()

    # Act
    result = text_filter.filter([house], criteria)

    # Assert
    assert result["test-house"].passed == expected_passed


# --- TextFilter multiple houses ---


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
    """TextFilter evaluates multiple houses independently."""
    # Arrange
    houses = [make_house(slug=slug, listing_text=text) for slug, text in houses_texts]
    text_filter = TextFilter()

    # Act
    results = text_filter.filter(houses, criteria)

    # Assert
    for slug, expected_passed in expected_results.items():
        assert results[slug].passed == expected_passed


# ===========================================================================
# Edge cases
# ===========================================================================

# --- TextFilter edge cases ---


def test_text_filter_whitespace_only_listing() -> None:
    """House with listing containing only whitespace fails p1 keyword check."""
    # Arrange
    house = make_house(slug="empty-house", listing_text="   \t  \n  ")
    text_filter = TextFilter()

    # Act
    result = text_filter.filter([house], {"p1_keywords": ["garden"]})

    # Assert
    assert result["empty-house"].passed is False


def test_text_filter_empty_keyword_lists() -> None:
    """Criteria with empty keyword lists passes any house."""
    # Arrange
    house = make_house(slug="any-house", listing_text="some listing text")
    text_filter = TextFilter()

    # Act
    result = text_filter.filter(
        [house], {"p1_keywords": [], "p2_keywords": [], "excluded_keywords": []}
    )

    # Assert
    assert result["any-house"].passed is True


def test_text_filter_unicode_keywords() -> None:
    """Unicode characters in keywords and listing text are matched correctly."""
    # Arrange
    house = make_house(slug="intl-house", listing_text="schöner Garten mit Küche und café")
    text_filter = TextFilter()

    # Act
    result = text_filter.filter([house], {"p1_keywords": ["garten", "küche"]})

    # Assert
    assert result["intl-house"].passed is True


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- Criteria with unexpected types ---


def test_text_filter_none_keyword_list_raises() -> None:
    """TextFilter raises TypeError when a criteria keyword list is None."""
    # Arrange
    house = make_house(slug="test-house", listing_text="garden with pool")
    text_filter = TextFilter()

    # Act & Assert
    with pytest.raises(TypeError):
        text_filter.filter([house], {"p1_keywords": None})


def test_text_filter_non_string_keyword_raises() -> None:
    """TextFilter raises AttributeError when keywords contain non-string values."""
    # Arrange
    house = make_house(slug="test-house", listing_text="garden with pool")
    text_filter = TextFilter()

    # Act & Assert
    with pytest.raises(AttributeError):
        text_filter.filter([house], {"p1_keywords": [123]})
