"""Unit tests for House and related models."""

from typing import NamedTuple

import pytest

from src.models.house import FilterResult, House, HouseMetadata, HouseStatus
from src.models.room import Photo, Room, RoomType

# ---------------------------------------------------------------------------
# Photo — creation
# ---------------------------------------------------------------------------


class PhotoCreationCase(NamedTuple):
    """Test case for Photo model creation."""

    description: str
    filename: str
    path: str
    room_type: RoomType | None
    confidence: float | None
    detected_features: list
    expected_imagineered_path: str | None


PHOTO_CREATION_CASES = [
    PhotoCreationCase(
        description="minimal photo with just filename and path has all defaults",
        filename="001.jpg",
        path="photos/001.jpg",
        room_type=None,
        confidence=None,
        detected_features=[],
        expected_imagineered_path=None,
    ),
    PhotoCreationCase(
        description="classified photo stores room type confidence and features",
        filename="kitchen.jpg",
        path="photos/kitchen.jpg",
        room_type=RoomType.KITCHEN,
        confidence=0.95,
        detected_features=["modern_appliances", "natural_light"],
        expected_imagineered_path=None,
    ),
]


@pytest.mark.parametrize(
    "description, filename, path, room_type, confidence, "
    "detected_features, expected_imagineered_path",
    PHOTO_CREATION_CASES,
)
def test_photo_creation(
    description: str,
    filename: str,
    path: str,
    room_type: RoomType | None,
    confidence: float | None,
    detected_features: list,
    expected_imagineered_path: str | None,
) -> None:
    photo = Photo(
        filename=filename,
        path=path,
        room_type=room_type,
        confidence=confidence,
        detected_features=detected_features,
    )
    assert photo.filename == filename
    assert photo.path == path
    assert photo.room_type == room_type
    assert photo.confidence == confidence
    assert photo.detected_features == detected_features
    assert photo.imagineered_path == expected_imagineered_path


# ---------------------------------------------------------------------------
# Photo — immutability
# ---------------------------------------------------------------------------


class PhotoFrozenCase(NamedTuple):
    """Test case for Photo model immutability."""

    description: str
    filename: str
    path: str


PHOTO_FROZEN_CASES = [
    PhotoFrozenCase(
        description="photo model raises an exception when mutated",
        filename="001.jpg",
        path="photos/001.jpg",
    ),
]


@pytest.mark.parametrize("description, filename, path", PHOTO_FROZEN_CASES)
def test_photo_is_frozen(description: str, filename: str, path: str) -> None:
    photo = Photo(filename=filename, path=path)
    with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
        photo.filename = "changed.jpg"


# ---------------------------------------------------------------------------
# Photo — confidence bounds
# ---------------------------------------------------------------------------


class PhotoInvalidConfidenceCase(NamedTuple):
    """Test case for invalid Photo confidence values."""

    description: str
    confidence: float


PHOTO_INVALID_CONFIDENCE_CASES = [
    PhotoInvalidConfidenceCase(
        description="confidence above 1.0 is invalid",
        confidence=1.5,
    ),
    PhotoInvalidConfidenceCase(
        description="confidence below 0 is invalid",
        confidence=-0.1,
    ),
]


@pytest.mark.parametrize("description, confidence", PHOTO_INVALID_CONFIDENCE_CASES)
def test_photo_confidence_bounds(description: str, confidence: float) -> None:
    with pytest.raises(ValueError):
        Photo(filename="001.jpg", path="photos/001.jpg", confidence=confidence)


# ---------------------------------------------------------------------------
# Room — creation
# ---------------------------------------------------------------------------


class RoomCreationCase(NamedTuple):
    """Test case for Room model creation."""

    description: str
    room_type: RoomType
    photos: list
    expected_photo_count: int


ROOM_CREATION_CASES = [
    RoomCreationCase(
        description="room with two photos has photo_count of two",
        room_type=RoomType.BEDROOM,
        photos=[
            Photo(filename="bed1.jpg", path="photos/bed1.jpg"),
            Photo(filename="bed2.jpg", path="photos/bed2.jpg"),
        ],
        expected_photo_count=2,
    ),
    RoomCreationCase(
        description="room without photos has photo_count of zero and empty list",
        room_type=RoomType.KITCHEN,
        photos=[],
        expected_photo_count=0,
    ),
]


@pytest.mark.parametrize(
    "description, room_type, photos, expected_photo_count", ROOM_CREATION_CASES
)
def test_room_creation(
    description: str,
    room_type: RoomType,
    photos: list,
    expected_photo_count: int,
) -> None:
    room = Room(room_type=room_type, photos=photos)
    assert room.room_type == room_type
    assert room.photo_count == expected_photo_count
    if not photos:
        assert room.photos == []


# ---------------------------------------------------------------------------
# Room — RoomType enum completeness
# ---------------------------------------------------------------------------


class RoomTypeEnumCase(NamedTuple):
    """Test case for RoomType enum completeness."""

    description: str
    expected_values: set


ROOM_TYPE_ENUM_CASES = [
    RoomTypeEnumCase(
        description="all expected room type values are present in the enum",
        expected_values={
            "living_room",
            "bedroom",
            "kitchen",
            "bathroom",
            "toilet",
            "hallway",
            "garden",
            "balcony",
            "garage",
            "storage",
            "office",
            "dining_room",
            "laundry",
            "basement",
            "attic",
            "exterior",
            "floor_plan",
            "other",
            "unknown",
        },
    ),
]


@pytest.mark.parametrize("description, expected_values", ROOM_TYPE_ENUM_CASES)
def test_room_types_enum(description: str, expected_values: set) -> None:
    actual = {rt.value for rt in RoomType}
    assert expected_values == actual


# ---------------------------------------------------------------------------
# HouseMetadata — creation
# ---------------------------------------------------------------------------


class HouseMetadataCreationCase(NamedTuple):
    """Test case for HouseMetadata creation."""

    description: str
    kwargs: dict
    expected_address: str | None
    expected_city: str | None
    expected_price: int | None


HOUSE_METADATA_CREATION_CASES = [
    HouseMetadataCreationCase(
        description="empty metadata initialises all fields to None",
        kwargs={},
        expected_address=None,
        expected_city=None,
        expected_price=None,
    ),
    HouseMetadataCreationCase(
        description="full metadata stores all provided fields correctly",
        kwargs={
            "address": "123 Main St",
            "city": "Amsterdam",
            "postal_code": "1234AB",
            "price": 450000,
            "living_area_m2": 85,
            "num_rooms": 4,
        },
        expected_address="123 Main St",
        expected_city="Amsterdam",
        expected_price=450000,
    ),
]


@pytest.mark.parametrize(
    "description, kwargs, expected_address, expected_city, expected_price",
    HOUSE_METADATA_CREATION_CASES,
)
def test_house_metadata_creation(
    description: str,
    kwargs: dict,
    expected_address: str | None,
    expected_city: str | None,
    expected_price: int | None,
) -> None:
    meta = HouseMetadata(**kwargs)
    assert meta.address == expected_address
    assert meta.city == expected_city
    assert meta.price == expected_price


# ---------------------------------------------------------------------------
# HouseMetadata — invalid price
# ---------------------------------------------------------------------------


class HouseMetadataInvalidPriceCase(NamedTuple):
    """Test case for invalid HouseMetadata price values."""

    description: str
    price: int


HOUSE_METADATA_INVALID_PRICE_CASES = [
    HouseMetadataInvalidPriceCase(
        description="negative price raises ValueError",
        price=-1,
    ),
]


@pytest.mark.parametrize("description, price", HOUSE_METADATA_INVALID_PRICE_CASES)
def test_house_metadata_price_non_negative(description: str, price: int) -> None:
    with pytest.raises(ValueError):
        HouseMetadata(price=price)


# ---------------------------------------------------------------------------
# House — creation
# ---------------------------------------------------------------------------


class HouseCreationCase(NamedTuple):
    """Test case for minimal House creation."""

    description: str
    slug: str
    expected_status: HouseStatus
    expected_photo_count: int
    expected_room_count: int


HOUSE_CREATION_CASES = [
    HouseCreationCase(
        description="minimal house with slug starts in RAW status with no rooms or photos",
        slug="my-house",
        expected_status=HouseStatus.RAW,
        expected_photo_count=0,
        expected_room_count=0,
    ),
]


@pytest.mark.parametrize(
    "description, slug, expected_status, expected_photo_count, expected_room_count",
    HOUSE_CREATION_CASES,
)
def test_house_creation(
    description: str,
    slug: str,
    expected_status: HouseStatus,
    expected_photo_count: int,
    expected_room_count: int,
) -> None:
    house = House(slug=slug)
    assert house.slug == slug
    assert house.status == expected_status
    assert house.photo_count == expected_photo_count
    assert house.room_count == expected_room_count


# ---------------------------------------------------------------------------
# House — with rooms
# ---------------------------------------------------------------------------


class HouseWithRoomsCase(NamedTuple):
    """Test case for House with rooms."""

    description: str
    rooms: list
    expected_room_count: int
    expected_bedroom_count: int
    expected_has_garden: bool
    expected_has_balcony: bool


HOUSE_WITH_ROOMS_CASES = [
    HouseWithRoomsCase(
        description="house with two bedrooms kitchen and garden counts all room types correctly",
        rooms=[
            Room(room_type=RoomType.BEDROOM),
            Room(room_type=RoomType.BEDROOM),
            Room(room_type=RoomType.KITCHEN),
            Room(room_type=RoomType.GARDEN),
        ],
        expected_room_count=4,
        expected_bedroom_count=2,
        expected_has_garden=True,
        expected_has_balcony=False,
    ),
]


@pytest.mark.parametrize(
    "description, rooms, expected_room_count, expected_bedroom_count, "
    "expected_has_garden, expected_has_balcony",
    HOUSE_WITH_ROOMS_CASES,
)
def test_house_with_rooms(
    description: str,
    rooms: list,
    expected_room_count: int,
    expected_bedroom_count: int,
    expected_has_garden: bool,
    expected_has_balcony: bool,
) -> None:
    house = House(slug="my-house", rooms=rooms)
    assert house.room_count == expected_room_count
    assert house.bedroom_count == expected_bedroom_count
    assert house.has_garden == expected_has_garden
    assert house.has_balcony == expected_has_balcony


# ---------------------------------------------------------------------------
# House — filter result tracking
# ---------------------------------------------------------------------------


class FilterResultTrackingCase(NamedTuple):
    """Test case for House filter result accumulation."""

    description: str
    house_slug: str


FILTER_RESULT_TRACKING_CASES = [
    FilterResultTrackingCase(
        description="successive filter results merge without losing earlier results",
        house_slug="test-house",
    ),
]


@pytest.mark.parametrize("description, house_slug", FILTER_RESULT_TRACKING_CASES)
def test_filter_result_tracking(description: str, house_slug: str) -> None:
    house = House(slug=house_slug)

    result1 = FilterResult(p1={"garden": True})
    house2 = house.with_filter_result(result1)
    assert house2.filter_results.p1["garden"] is True

    result2 = FilterResult(p2={"garage": False})
    house3 = house2.with_filter_result(result2)
    assert house3.filter_results.p2["garage"] is False
    assert house3.filter_results.p1["garden"] is True


# ---------------------------------------------------------------------------
# House — immutability
# ---------------------------------------------------------------------------


class HouseImmutabilityCase(NamedTuple):
    """Test case for House immutability via with_status."""

    description: str
    slug: str
    new_status: HouseStatus


HOUSE_IMMUTABILITY_CASES = [
    HouseImmutabilityCase(
        description="with_status returns a new House instance without mutating the original",
        slug="test",
        new_status=HouseStatus.CLASSIFIED,
    ),
]


@pytest.mark.parametrize("description, slug, new_status", HOUSE_IMMUTABILITY_CASES)
def test_house_immutability(description: str, slug: str, new_status: HouseStatus) -> None:
    house1 = House(slug=slug)
    house2 = house1.with_status(new_status)

    assert house1.status == HouseStatus.RAW
    assert house2.status == new_status
    assert house1 is not house2


# ---------------------------------------------------------------------------
# House — HouseStatus enum completeness
# ---------------------------------------------------------------------------


class HouseStatusEnumCase(NamedTuple):
    """Test case for HouseStatus enum completeness."""

    description: str
    expected_values: set


HOUSE_STATUS_ENUM_CASES = [
    HouseStatusEnumCase(
        description="all expected house status values are present in the enum",
        expected_values={"raw", "filtered", "classified", "evaluated", "imagineered", "complete"},
    ),
]


@pytest.mark.parametrize("description, expected_values", HOUSE_STATUS_ENUM_CASES)
def test_house_status_values(description: str, expected_values: set) -> None:
    actual = {s.value for s in HouseStatus}
    assert expected_values == actual



