"""Unit tests for the LLM text filter service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple
from unittest.mock import MagicMock

import pytest

from src.models.house import House
from src.models.text_analysis import CriterionResult, TextAnalysis
from src.services.text_filter_service import (
    LLMTextFilterService,
    _build_criteria_list,
    _compute_criteria_hash,
    _CriterionEval,
    _TextAnalysisResult,
)

# ---------------------------------------------------------------------------
# Helpers / NamedTuples / test case lists
# ---------------------------------------------------------------------------

_SAMPLE_CRITERIA: dict[str, Any] = {
    "p1_criteria": [
        "has a private garden or outdoor space",
        "has at least 3 bedrooms",
    ],
    "p2_criteria": [
        "has a garage or covered parking",
    ],
    "excluded_criteria": [
        "located near a highway or industrial area",
    ],
}

_SAMPLE_LISTING = (
    "Beautiful 4-bedroom house with a spacious private garden. "
    "Modern kitchen with dishwasher. Quiet residential neighbourhood."
)


def _make_house(slug: str = "test-house", listing_text: str = _SAMPLE_LISTING) -> House:
    """Create a minimal House for testing."""
    return House(slug=slug, listing_text=listing_text)


def _make_llm_response(
    evals: list[dict[str, Any]] | None = None,
) -> _TextAnalysisResult:
    """Build a fake LLM structured response."""
    if evals is None:
        evals = [
            {
                "criterion_name": "has a private garden or outdoor space",
                "met": True,
                "confidence": 0.95,
                "reasoning": "Listing mentions a spacious private garden.",
            },
            {
                "criterion_name": "has at least 3 bedrooms",
                "met": True,
                "confidence": 0.90,
                "reasoning": "Listing says 4-bedroom house.",
            },
            {
                "criterion_name": "has a garage or covered parking",
                "met": False,
                "confidence": 0.80,
                "reasoning": "No mention of garage or parking.",
            },
            {
                "criterion_name": "located near a highway or industrial area",
                "met": False,
                "confidence": 0.85,
                "reasoning": "Described as quiet residential neighbourhood.",
            },
        ]
    return _TextAnalysisResult(
        evaluations=[_CriterionEval(**ev) for ev in evals],
    )


def _make_service(
    tmp_path: Path,
    llm_response: _TextAnalysisResult | None = None,
) -> tuple[LLMTextFilterService, MagicMock]:
    """Create an LLMTextFilterService with a mocked ILLMService."""
    mock_llm = MagicMock()
    mock_llm.complete_structured.return_value = (
        llm_response if llm_response is not None else _make_llm_response()
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    service = LLMTextFilterService(
        llm_service=mock_llm,
        output_dir=output_dir,
    )
    return service, mock_llm


class CriteriaHashCase(NamedTuple):
    """Test case for criteria hash computation."""

    description: str
    criteria_a: dict[str, Any]
    criteria_b: dict[str, Any]
    should_match: bool


CRITERIA_HASH_CASES = [
    CriteriaHashCase(
        description="identical criteria produce the same hash",
        criteria_a={"p1_criteria": ["garden"]},
        criteria_b={"p1_criteria": ["garden"]},
        should_match=True,
    ),
    CriteriaHashCase(
        description="different criteria produce different hashes",
        criteria_a={"p1_criteria": ["garden"]},
        criteria_b={"p1_criteria": ["pool"]},
        should_match=False,
    ),
    CriteriaHashCase(
        description="key order does not affect hash",
        criteria_a={"p1_criteria": ["a"], "p2_criteria": ["b"]},
        criteria_b={"p2_criteria": ["b"], "p1_criteria": ["a"]},
        should_match=True,
    ),
]


class CriteriaListCase(NamedTuple):
    """Test case for building the flat criteria list."""

    description: str
    criteria: dict[str, Any]
    expected: list[tuple[str, str]]


CRITERIA_LIST_CASES = [
    CriteriaListCase(
        description="all categories are included",
        criteria={
            "p1_criteria": ["garden"],
            "p2_criteria": ["garage"],
            "excluded_criteria": ["highway"],
        },
        expected=[("garden", "p1"), ("garage", "p2"), ("highway", "excluded")],
    ),
    CriteriaListCase(
        description="missing categories default to empty",
        criteria={"p1_criteria": ["garden"]},
        expected=[("garden", "p1")],
    ),
    CriteriaListCase(
        description="empty criteria dict produces empty list",
        criteria={},
        expected=[],
    ),
]


class FilterResultMappingCase(NamedTuple):
    """Test case for TextAnalysis -> FilterResult conversion."""

    description: str
    evaluations: list[CriterionResult]
    expected_p1: dict[str, bool]
    expected_p2: dict[str, bool]
    expected_excluded: dict[str, bool]


FILTER_RESULT_CASES = [
    FilterResultMappingCase(
        description="p1/p2/excluded correctly populated",
        evaluations=[
            CriterionResult(
                criterion_name="garden",
                category="p1",
                met=True,
                confidence=0.9,
                reasoning="Has garden.",
            ),
            CriterionResult(
                criterion_name="garage",
                category="p2",
                met=False,
                confidence=0.8,
                reasoning="No garage.",
            ),
            CriterionResult(
                criterion_name="highway",
                category="excluded",
                met=False,
                confidence=0.7,
                reasoning="Not near highway.",
            ),
        ],
        expected_p1={"garden": True},
        expected_p2={"garage": False},
        expected_excluded={"highway": False},
    ),
    FilterResultMappingCase(
        description="empty evaluations produce empty FilterResult",
        evaluations=[],
        expected_p1={},
        expected_p2={},
        expected_excluded={},
    ),
    FilterResultMappingCase(
        description="multiple p1 criteria are all included",
        evaluations=[
            CriterionResult(
                criterion_name="garden",
                category="p1",
                met=True,
                confidence=0.9,
                reasoning="Yes.",
            ),
            CriterionResult(
                criterion_name="3 bedrooms",
                category="p1",
                met=False,
                confidence=0.6,
                reasoning="Only 2.",
            ),
        ],
        expected_p1={"garden": True, "3 bedrooms": False},
        expected_p2={},
        expected_excluded={},
    ),
]


class FilterFlowCase(NamedTuple):
    """Test case for the full LLM text filter flow."""

    description: str
    listing_text: str
    llm_evals: list[dict[str, Any]]
    expected_p1_values: list[bool]
    expected_excluded_values: list[bool]


FILTER_FLOW_CASES = [
    FilterFlowCase(
        description="house passes when all p1 met and no excluded",
        listing_text=_SAMPLE_LISTING,
        llm_evals=[
            {
                "criterion_name": "has a private garden or outdoor space",
                "met": True,
                "confidence": 0.95,
                "reasoning": "Has garden.",
            },
            {
                "criterion_name": "has at least 3 bedrooms",
                "met": True,
                "confidence": 0.90,
                "reasoning": "4 bedrooms.",
            },
            {
                "criterion_name": "has a garage or covered parking",
                "met": False,
                "confidence": 0.80,
                "reasoning": "No garage.",
            },
            {
                "criterion_name": "located near a highway or industrial area",
                "met": False,
                "confidence": 0.85,
                "reasoning": "Quiet area.",
            },
        ],
        expected_p1_values=[True, True],
        expected_excluded_values=[False],
    ),
    FilterFlowCase(
        description="house excluded when excluded criterion is met",
        listing_text="Near highway, industrial zone. 2 bedrooms.",
        llm_evals=[
            {
                "criterion_name": "has a private garden or outdoor space",
                "met": False,
                "confidence": 0.70,
                "reasoning": "No garden.",
            },
            {
                "criterion_name": "has at least 3 bedrooms",
                "met": False,
                "confidence": 0.85,
                "reasoning": "Only 2 bedrooms.",
            },
            {
                "criterion_name": "has a garage or covered parking",
                "met": False,
                "confidence": 0.90,
                "reasoning": "No garage.",
            },
            {
                "criterion_name": "located near a highway or industrial area",
                "met": True,
                "confidence": 0.95,
                "reasoning": "Near highway.",
            },
        ],
        expected_p1_values=[False, False],
        expected_excluded_values=[True],
    ),
]


class ModelSerializationCase(NamedTuple):
    """Test case for text analysis model round-trip."""

    description: str
    slug: str
    n_evaluations: int


MODEL_SERIALIZATION_CASES = [
    ModelSerializationCase(
        description="TextAnalysis round-trips through JSON",
        slug="canal-house",
        n_evaluations=3,
    ),
    ModelSerializationCase(
        description="empty evaluations list round-trips",
        slug="empty-house",
        n_evaluations=0,
    ),
]


# ===========================================================================
# Happy path
# ===========================================================================

# --- Criteria hash ---


@pytest.mark.parametrize(
    "description, criteria_a, criteria_b, should_match",
    CRITERIA_HASH_CASES,
)
def test_criteria_hash(
    description: str,
    criteria_a: dict[str, Any],
    criteria_b: dict[str, Any],
    should_match: bool,
) -> None:
    # Act
    hash_a = _compute_criteria_hash(criteria_a)
    hash_b = _compute_criteria_hash(criteria_b)

    # Assert
    if should_match:
        assert hash_a == hash_b
    else:
        assert hash_a != hash_b


# --- Criteria list building ---


@pytest.mark.parametrize("description, criteria, expected", CRITERIA_LIST_CASES)
def test_build_criteria_list(
    description: str,
    criteria: dict[str, Any],
    expected: list[tuple[str, str]],
) -> None:
    # Act
    result = _build_criteria_list(criteria)

    # Assert
    assert result == expected


# --- FilterResult mapping ---


@pytest.mark.parametrize(
    "description, evaluations, expected_p1, expected_p2, expected_excluded",
    FILTER_RESULT_CASES,
)
def test_filter_result_mapping(
    description: str,
    evaluations: list[CriterionResult],
    expected_p1: dict[str, bool],
    expected_p2: dict[str, bool],
    expected_excluded: dict[str, bool],
) -> None:
    # Arrange
    analysis = TextAnalysis(slug="test", criteria_hash="abc", evaluations=evaluations)

    # Act
    result = analysis.to_filter_result()

    # Assert
    assert result.p1 == expected_p1
    assert result.p2 == expected_p2
    assert result.excluded == expected_excluded


# --- Full filter flow ---


@pytest.mark.parametrize(
    "description, listing_text, llm_evals, expected_p1_values, expected_excluded_values",
    FILTER_FLOW_CASES,
)
def test_filter_flow(
    description: str,
    listing_text: str,
    llm_evals: list[dict[str, Any]],
    expected_p1_values: list[bool],
    expected_excluded_values: list[bool],
    tmp_path: Path,
) -> None:
    # Arrange
    response = _make_llm_response(llm_evals)
    service, mock_llm = _make_service(tmp_path, response)
    house = _make_house(listing_text=listing_text)

    # Act
    results = service.filter([house], _SAMPLE_CRITERIA)

    # Assert
    assert house.slug in results
    fr = results[house.slug]
    assert list(fr.p1.values()) == expected_p1_values
    assert list(fr.excluded.values()) == expected_excluded_values
    mock_llm.complete_structured.assert_called_once()


# --- Caching behaviour ---


def test_cache_hit_skips_llm_call(tmp_path: Path) -> None:
    """When cached analysis exists with matching criteria hash, skip the LLM."""
    # Arrange
    service, mock_llm = _make_service(tmp_path)
    house = _make_house()
    service.filter([house], _SAMPLE_CRITERIA)
    assert mock_llm.complete_structured.call_count == 1

    # Act
    service.filter([house], _SAMPLE_CRITERIA)

    # Assert
    assert mock_llm.complete_structured.call_count == 1


# --- Cache file persistence ---


def test_results_written_to_cache_file(tmp_path: Path) -> None:
    """Filter results are persisted to the expected output file."""
    # Arrange
    service, _ = _make_service(tmp_path)
    house = _make_house()

    # Act
    service.filter([house], _SAMPLE_CRITERIA)

    # Assert
    cache_file = tmp_path / "output" / house.slug / "text_analysis.json"
    assert cache_file.exists()

    data = json.loads(cache_file.read_text(encoding="utf-8"))
    analysis = TextAnalysis(**data)
    assert analysis.slug == house.slug
    assert len(analysis.evaluations) == 4


# --- Model serialization ---


@pytest.mark.parametrize(
    "description, slug, n_evaluations",
    MODEL_SERIALIZATION_CASES,
)
def test_model_serialization(
    description: str,
    slug: str,
    n_evaluations: int,
) -> None:
    # Arrange
    evaluations = [
        CriterionResult(
            criterion_name=f"criterion_{i}",
            category="p1",
            met=i % 2 == 0,
            confidence=0.8,
            reasoning=f"Reason {i}",
        )
        for i in range(n_evaluations)
    ]
    analysis = TextAnalysis(
        slug=slug,
        criteria_hash="abc123",
        evaluations=evaluations,
    )

    # Act
    data = analysis.model_dump()
    restored = TextAnalysis(**data)

    # Assert
    assert restored == analysis
    assert len(restored.evaluations) == n_evaluations


# --- Multiple houses ---


def test_multiple_houses_processed(tmp_path: Path) -> None:
    """Each house gets its own analysis and cache file."""
    # Arrange
    service, mock_llm = _make_service(tmp_path)
    houses = [_make_house(slug="house-a"), _make_house(slug="house-b")]

    # Act
    results = service.filter(houses, _SAMPLE_CRITERIA)

    # Assert
    assert len(results) == 2
    assert "house-a" in results
    assert "house-b" in results
    assert mock_llm.complete_structured.call_count == 2

    # Both cache files should exist
    assert (tmp_path / "output" / "house-a" / "text_analysis.json").exists()
    assert (tmp_path / "output" / "house-b" / "text_analysis.json").exists()


# --- Name property ---


def test_name_property(tmp_path: Path) -> None:
    """Service reports 'llm_text_filter' as its name."""
    # Arrange
    service, _ = _make_service(tmp_path)

    # Act & Assert
    assert service.name == "llm_text_filter"


# ===========================================================================
# Edge cases
# ===========================================================================

# --- Criteria drift ---


def test_criteria_drift_triggers_reanalysis(tmp_path: Path) -> None:
    """When criteria change, the cached result should be ignored."""
    # Arrange
    service, mock_llm = _make_service(tmp_path)
    house = _make_house()
    service.filter([house], _SAMPLE_CRITERIA)
    assert mock_llm.complete_structured.call_count == 1
    changed_criteria = {
        "p1_criteria": ["has a swimming pool"],
        "p2_criteria": [],
        "excluded_criteria": [],
    }
    # Update the LLM mock for the new criteria
    mock_llm.complete_structured.return_value = _TextAnalysisResult(
        evaluations=[
            _CriterionEval(
                criterion_name="has a swimming pool",
                met=False,
                confidence=0.70,
                reasoning="No pool mentioned.",
            ),
        ],
    )

    # Act
    service.filter([house], changed_criteria)

    # Assert
    assert mock_llm.complete_structured.call_count == 2


# --- Corrupt cache ---


def test_corrupt_cache_triggers_reanalysis(tmp_path: Path) -> None:
    """When the cache file is corrupt JSON, the service should re-analyze."""
    # Arrange
    service, mock_llm = _make_service(tmp_path)
    house = _make_house()
    cache_file = tmp_path / "output" / house.slug / "text_analysis.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{ not valid json", encoding="utf-8")

    # Act
    service.filter([house], _SAMPLE_CRITERIA)

    # Assert
    assert mock_llm.complete_structured.call_count == 1


# ===========================================================================
# Error / failure cases
# ===========================================================================

# --- LLM error propagation ---


def test_llm_error_propagates(tmp_path: Path) -> None:
    """LLM service errors should propagate to the caller."""
    # Arrange
    mock_llm = MagicMock()
    mock_llm.complete_structured.side_effect = RuntimeError("LLM unavailable")
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    service = LLMTextFilterService(llm_service=mock_llm, output_dir=output_dir)
    house = _make_house()

    # Act & Assert
    with pytest.raises(RuntimeError, match="LLM unavailable"):
        service.filter([house], _SAMPLE_CRITERIA)
