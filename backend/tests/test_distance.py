"""Unit tests for the distance calculator service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple
from unittest.mock import MagicMock, patch

import pytest

from src.config import load_distance_config
from src.models.distance import DistanceResult, TravelTime
from src.services.distance_calculator import GoogleMapsDistanceCalculator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_API_KEY = "test-google-maps-key"

_SAMPLE_DESTINATIONS = [
    {"name": "Amsterdam Central", "address": "Amsterdam Centraal, Amsterdam", "modes": ["transit"]},
    {"name": "Office", "address": "Zuidas, Amsterdam", "modes": ["driving", "transit"]},
]


def _make_api_response(
    duration_seconds: int = 1500,
    duration_text: str = "25 mins",
    status: str = "OK",
    element_status: str = "OK",
) -> dict:
    """Build a fake Google Maps Distance Matrix API response."""
    return {
        "status": status,
        "rows": [
            {
                "elements": [
                    {
                        "status": element_status,
                        "duration": {
                            "value": duration_seconds,
                            "text": duration_text,
                        },
                        "distance": {"value": 12000, "text": "12 km"},
                    }
                ]
            }
        ],
    }


def _setup_house(
    tmp_path: Path,
    slug: str,
    listing_text: str = "Address: Keizersgracht 100, Amsterdam\nA lovely canal house.",
) -> tuple[Path, Path]:
    """Create a house input directory with a listing.txt file.

    Returns:
        (input_dir, output_dir) paths.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    house_dir = input_dir / slug
    house_dir.mkdir(parents=True)
    (house_dir / "listing.txt").write_text(listing_text, encoding="utf-8")

    output_dir.mkdir(parents=True)
    return input_dir, output_dir


def _make_service(
    input_dir: Path,
    output_dir: Path,
    destinations: list[dict] | None = None,
) -> GoogleMapsDistanceCalculator:
    """Create a GoogleMapsDistanceCalculator with test defaults."""
    return GoogleMapsDistanceCalculator(
        api_key=_FAKE_API_KEY,
        input_dir=input_dir,
        output_dir=output_dir,
        destinations=destinations or _SAMPLE_DESTINATIONS,
    )


# ---------------------------------------------------------------------------
# Model serialization
# ---------------------------------------------------------------------------


class TravelTimeSerializationCase(NamedTuple):
    """Test case for TravelTime model round-trip."""

    description: str
    travel_time: TravelTime
    expected_minutes: int


TRAVEL_TIME_SERIALIZATION_CASES = [
    TravelTimeSerializationCase(
        description="TravelTime round-trips through dict serialization",
        travel_time=TravelTime(
            destination_name="Amsterdam Central",
            destination_address="Amsterdam Centraal",
            mode="transit",
            duration_minutes=25,
            duration_text="25 mins",
        ),
        expected_minutes=25,
    ),
    TravelTimeSerializationCase(
        description="TravelTime preserves cycling mode",
        travel_time=TravelTime(
            destination_name="Office",
            destination_address="Zuidas, Amsterdam",
            mode="cycling",
            duration_minutes=15,
            duration_text="15 mins",
        ),
        expected_minutes=15,
    ),
]


@pytest.mark.parametrize(
    "description, travel_time, expected_minutes", TRAVEL_TIME_SERIALIZATION_CASES
)
def test_travel_time_serialization(
    description: str,
    travel_time: TravelTime,
    expected_minutes: int,
) -> None:
    data = travel_time.model_dump()
    restored = TravelTime(**data)
    assert restored.duration_minutes == expected_minutes
    assert restored == travel_time


# ---------------------------------------------------------------------------
# DistanceResult container
# ---------------------------------------------------------------------------


class DistanceResultCase(NamedTuple):
    """Test case for DistanceResult container."""

    description: str
    slug: str
    destination_count: int


DISTANCE_RESULT_CASES = [
    DistanceResultCase(
        description="empty result has no destinations",
        slug="test-house",
        destination_count=0,
    ),
    DistanceResultCase(
        description="result holds multiple destinations",
        slug="canal-house",
        destination_count=3,
    ),
]


@pytest.mark.parametrize("description, slug, destination_count", DISTANCE_RESULT_CASES)
def test_distance_result_container(description: str, slug: str, destination_count: int) -> None:
    destinations = [
        TravelTime(
            destination_name=f"Dest {i}",
            destination_address=f"Addr {i}",
            mode="transit",
            duration_minutes=10 * (i + 1),
            duration_text=f"{10 * (i + 1)} mins",
        )
        for i in range(destination_count)
    ]
    result = DistanceResult(slug=slug, destinations=destinations)
    assert result.slug == slug
    assert len(result.destinations) == destination_count


# ---------------------------------------------------------------------------
# DistanceResult summary/detailed dicts
# ---------------------------------------------------------------------------


class SummaryDictCase(NamedTuple):
    """Test case for to_summary_dict."""

    description: str
    destinations: list[TravelTime]
    expected_keys: list[str]


SUMMARY_DICT_CASES = [
    SummaryDictCase(
        description="summary dict has destination (mode) keys",
        destinations=[
            TravelTime(
                destination_name="Central",
                destination_address="Centraal",
                mode="transit",
                duration_minutes=25,
                duration_text="25 mins",
            ),
        ],
        expected_keys=["Central (transit)"],
    ),
    SummaryDictCase(
        description="empty destinations produce empty dict",
        destinations=[],
        expected_keys=[],
    ),
]


@pytest.mark.parametrize("description, destinations, expected_keys", SUMMARY_DICT_CASES)
def test_summary_dict(
    description: str, destinations: list[TravelTime], expected_keys: list[str]
) -> None:
    result = DistanceResult(slug="test", destinations=destinations)
    summary = result.to_summary_dict()
    assert list(summary.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Service — successful calculation
# ---------------------------------------------------------------------------


class CalculationCase(NamedTuple):
    """Test case for successful distance calculation."""

    description: str
    destinations: list[dict]
    expected_result_count: int


CALCULATION_CASES = [
    CalculationCase(
        description="single destination single mode produces one result",
        destinations=[
            {"name": "Central", "address": "Amsterdam Centraal", "modes": ["transit"]},
        ],
        expected_result_count=1,
    ),
    CalculationCase(
        description="one destination two modes produces two results",
        destinations=[
            {"name": "Office", "address": "Zuidas", "modes": ["driving", "transit"]},
        ],
        expected_result_count=2,
    ),
    CalculationCase(
        description="two destinations produce two results",
        destinations=[
            {"name": "Central", "address": "Centraal", "modes": ["transit"]},
            {"name": "Office", "address": "Zuidas", "modes": ["driving"]},
        ],
        expected_result_count=2,
    ),
]


@pytest.mark.parametrize("description, destinations, expected_result_count", CALCULATION_CASES)
def test_calculation_success(
    tmp_path: Path,
    description: str,
    destinations: list[dict],
    expected_result_count: int,
) -> None:
    input_dir, output_dir = _setup_house(tmp_path, "test-house")
    service = _make_service(input_dir, output_dir, destinations)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _make_api_response()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.services.distance_calculator.requests.get", return_value=mock_resp) as mock_get:
        result = service.calculate_distances("test-house")

    assert len(result.destinations) == expected_result_count
    assert result.origin_address == "Keizersgracht 100, Amsterdam"
    assert mock_get.call_count == expected_result_count

    # Verify output file was written
    output_file = output_dir / "test-house" / "distances.json"
    assert output_file.exists()


# ---------------------------------------------------------------------------
# Service — idempotent behavior
# ---------------------------------------------------------------------------


class IdempotentCase(NamedTuple):
    """Test case for idempotent distance calculation."""

    description: str
    recalculate: bool
    change_config: bool
    expected_api_calls: int


IDEMPOTENT_CASES = [
    IdempotentCase(
        description="skips calculation when results exist and config unchanged",
        recalculate=False,
        change_config=False,
        expected_api_calls=0,
    ),
    IdempotentCase(
        description="recalculates when config changes",
        recalculate=True,
        change_config=True,
        expected_api_calls=1,
    ),
]


@pytest.mark.parametrize(
    "description, recalculate, change_config, expected_api_calls",
    IDEMPOTENT_CASES,
)
def test_idempotent_behavior(
    tmp_path: Path,
    description: str,
    recalculate: bool,
    change_config: bool,
    expected_api_calls: int,
) -> None:
    destinations = [
        {"name": "Central", "address": "Centraal", "modes": ["transit"]},
    ]
    input_dir, output_dir = _setup_house(tmp_path, "test-house")
    service = _make_service(input_dir, output_dir, destinations)

    # Write pre-existing results with matching config hash
    existing_data = {
        "slug": "test-house",
        "origin_address": "Keizersgracht 100, Amsterdam",
        "destinations": [
            {
                "destination_name": "Central",
                "destination_address": "Centraal",
                "mode": "transit",
                "duration_minutes": 25,
                "duration_text": "25 mins",
            }
        ],
        "config_hash": service._config_hash(),
    }
    results_dir = output_dir / "test-house"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "distances.json").write_text(
        json.dumps(existing_data, indent=2) + "\n",
        encoding="utf-8",
    )

    if change_config:
        # Recreate service with different destinations so config hash won't match
        destinations = [
            {"name": "New Place", "address": "New Address", "modes": ["walking"]},
        ]
        service = _make_service(input_dir, output_dir, destinations)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _make_api_response()
    mock_resp.raise_for_status = MagicMock()

    with patch("src.services.distance_calculator.requests.get", return_value=mock_resp) as mock_get:
        result = service.calculate_distances("test-house")

    assert mock_get.call_count == expected_api_calls
    assert result.slug == "test-house"


# ---------------------------------------------------------------------------
# Service — address extraction
# ---------------------------------------------------------------------------


class AddressExtractionCase(NamedTuple):
    """Test case for address extraction from listing text."""

    description: str
    listing_text: str
    expected_address: str


ADDRESS_EXTRACTION_CASES = [
    AddressExtractionCase(
        description="extracts address from 'Address:' line",
        listing_text="Address: Keizersgracht 100, Amsterdam\nRest of listing.",
        expected_address="Keizersgracht 100, Amsterdam",
    ),
    AddressExtractionCase(
        description="extracts address from 'Adres:' line (Dutch)",
        listing_text="Adres: Prinsengracht 300, Amsterdam\nMooi huis.",
        expected_address="Prinsengracht 300, Amsterdam",
    ),
    AddressExtractionCase(
        description="falls back to first line when no Address label",
        listing_text="Herengracht 50, Amsterdam\nBeautiful property.",
        expected_address="Herengracht 50, Amsterdam",
    ),
    AddressExtractionCase(
        description="returns empty string for empty listing",
        listing_text="",
        expected_address="",
    ),
]


@pytest.mark.parametrize("description, listing_text, expected_address", ADDRESS_EXTRACTION_CASES)
def test_address_extraction(
    tmp_path: Path,
    description: str,
    listing_text: str,
    expected_address: str,
) -> None:
    input_dir, output_dir = _setup_house(tmp_path, "test-house", listing_text)
    service = _make_service(input_dir, output_dir)
    address = service._extract_address("test-house")
    assert address == expected_address


# ---------------------------------------------------------------------------
# Service — API error handling
# ---------------------------------------------------------------------------


class ErrorCase(NamedTuple):
    """Test case for API error handling."""

    description: str
    api_response: dict
    expected_result_count: int


ERROR_CASES = [
    ErrorCase(
        description="handles top-level API error status",
        api_response={"status": "REQUEST_DENIED", "rows": []},
        expected_result_count=0,
    ),
    ErrorCase(
        description="handles element-level ZERO_RESULTS",
        api_response={
            "status": "OK",
            "rows": [{"elements": [{"status": "ZERO_RESULTS"}]}],
        },
        expected_result_count=0,
    ),
    ErrorCase(
        description="handles empty rows",
        api_response={"status": "OK", "rows": []},
        expected_result_count=0,
    ),
]


@pytest.mark.parametrize("description, api_response, expected_result_count", ERROR_CASES)
def test_api_error_handling(
    tmp_path: Path,
    description: str,
    api_response: dict,
    expected_result_count: int,
) -> None:
    destinations = [
        {"name": "Central", "address": "Centraal", "modes": ["transit"]},
    ]
    input_dir, output_dir = _setup_house(tmp_path, "test-house")
    service = _make_service(input_dir, output_dir, destinations)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = api_response
    mock_resp.raise_for_status = MagicMock()

    with patch("src.services.distance_calculator.requests.get", return_value=mock_resp):
        result = service.calculate_distances("test-house")

    assert len(result.destinations) == expected_result_count


# ---------------------------------------------------------------------------
# Service — missing listing
# ---------------------------------------------------------------------------


def test_missing_listing_returns_empty(tmp_path: Path) -> None:
    """Returns empty DistanceResult when listing.txt is missing."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    service = _make_service(input_dir, output_dir)
    result = service.calculate_distances("no-house")
    assert result.slug == "no-house"
    assert result.origin_address == ""
    assert len(result.destinations) == 0


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def test_load_distance_config(tmp_path: Path) -> None:
    """load_distance_config returns the destinations list from YAML."""
    config_content = """
storage:
  input_dir: "input_data/houses"
  output_dir: "outputs/houses"

distance:
  destinations:
    - name: "Central Station"
      address: "Amsterdam Centraal"
      modes: ["transit", "cycling"]
    - name: "Airport"
      address: "Schiphol"
      modes: ["driving"]
"""
    config_file = tmp_path / "criteria.yaml"
    config_file.write_text(config_content, encoding="utf-8")

    destinations = load_distance_config(config_file)
    assert len(destinations) == 2
    assert destinations[0]["name"] == "Central Station"
    assert destinations[0]["modes"] == ["transit", "cycling"]
    assert destinations[1]["name"] == "Airport"


def test_load_distance_config_missing_section(tmp_path: Path) -> None:
    """load_distance_config raises KeyError when distance section is missing."""
    config_content = """
storage:
  input_dir: "input_data/houses"
  output_dir: "outputs/houses"
"""
    config_file = tmp_path / "criteria.yaml"
    config_file.write_text(config_content, encoding="utf-8")

    with pytest.raises(KeyError):
        load_distance_config(config_file)
