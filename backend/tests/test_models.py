"""Unit tests for House and related models."""

import pytest

from src.models.house import FilterResult, House, HouseMetadata, HouseStatus
from src.models.room import Photo, Room, RoomType


class TestPhoto:
    """Tests for the Photo model."""

    def test_create_minimal_photo(self):
        """Photo can be created with just filename and path."""
        photo = Photo(filename="001.jpg", path="photos/001.jpg")
        assert photo.filename == "001.jpg"
        assert photo.path == "photos/001.jpg"
        assert photo.room_type is None
        assert photo.confidence is None
        assert photo.detected_features == []
        assert photo.imagineered_path is None

    def test_create_classified_photo(self):
        """Photo can include classification data."""
        photo = Photo(
            filename="kitchen.jpg",
            path="photos/kitchen.jpg",
            room_type=RoomType.KITCHEN,
            confidence=0.95,
            detected_features=["modern_appliances", "natural_light"],
        )
        assert photo.room_type == RoomType.KITCHEN
        assert photo.confidence == 0.95
        assert "modern_appliances" in photo.detected_features

    def test_photo_is_frozen(self):
        """Photo should be immutable."""
        photo = Photo(filename="001.jpg", path="photos/001.jpg")
        with pytest.raises(Exception):  # Pydantic raises ValidationError for frozen models
            photo.filename = "changed.jpg"

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            Photo(filename="001.jpg", path="photos/001.jpg", confidence=1.5)
        with pytest.raises(ValueError):
            Photo(filename="001.jpg", path="photos/001.jpg", confidence=-0.1)


class TestRoom:
    """Tests for the Room model."""

    def test_create_room_with_photos(self):
        """Room can be created with photos."""
        photos = [
            Photo(filename="bed1.jpg", path="photos/bed1.jpg"),
            Photo(filename="bed2.jpg", path="photos/bed2.jpg"),
        ]
        room = Room(room_type=RoomType.BEDROOM, photos=photos)
        assert room.room_type == RoomType.BEDROOM
        assert room.photo_count == 2

    def test_empty_room(self):
        """Room can exist without photos."""
        room = Room(room_type=RoomType.KITCHEN)
        assert room.photo_count == 0
        assert room.photos == []

    def test_room_types_enum(self):
        """All expected room types exist."""
        expected = {
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
        }
        actual = {rt.value for rt in RoomType}
        assert expected == actual


class TestHouseMetadata:
    """Tests for the HouseMetadata model."""

    def test_empty_metadata(self):
        """Metadata can be created empty."""
        meta = HouseMetadata()
        assert meta.address is None
        assert meta.price is None

    def test_full_metadata(self):
        """Metadata can contain all fields."""
        meta = HouseMetadata(
            address="123 Main St",
            city="Amsterdam",
            postal_code="1234AB",
            price=450000,
            living_area_m2=85,
            num_rooms=4,
        )
        assert meta.address == "123 Main St"
        assert meta.city == "Amsterdam"
        assert meta.price == 450000

    def test_price_non_negative(self):
        """Price must be non-negative."""
        with pytest.raises(ValueError):
            HouseMetadata(price=-1)


class TestHouse:
    """Tests for the House model."""

    def test_create_minimal_house(self):
        """House can be created with just a slug."""
        house = House(slug="my-house")
        assert house.slug == "my-house"
        assert house.status == HouseStatus.RAW
        assert house.photo_count == 0
        assert house.room_count == 0

    def test_house_with_rooms(self):
        """House tracks rooms and counts correctly."""
        rooms = [
            Room(room_type=RoomType.BEDROOM),
            Room(room_type=RoomType.BEDROOM),
            Room(room_type=RoomType.KITCHEN),
            Room(room_type=RoomType.GARDEN),
        ]
        house = House(slug="my-house", rooms=rooms)
        assert house.room_count == 4
        assert house.bedroom_count == 2
        assert house.has_garden is True
        assert house.has_balcony is False

    def test_filter_result_tracking(self):
        """House tracks filter results correctly."""
        house = House(slug="test-house")

        result1 = FilterResult(p1={"garden": True})
        house2 = house.with_filter_result(result1)
        assert house2.filter_results.p1["garden"] is True

        result2 = FilterResult(p2={"garage": False})
        house3 = house2.with_filter_result(result2)
        assert house3.filter_results.p2["garage"] is False
        assert house3.filter_results.p1["garden"] is True

    def test_house_immutability(self):
        """House is immutable - updates return new instances."""
        house1 = House(slug="test")
        house2 = house1.with_status(HouseStatus.CLASSIFIED)

        assert house1.status == HouseStatus.RAW
        assert house2.status == HouseStatus.CLASSIFIED
        assert house1 is not house2

    def test_house_status_values(self):
        """All expected statuses exist."""
        expected = {"raw", "filtered", "classified", "evaluated", "imagineered", "complete"}
        actual = {s.value for s in HouseStatus}
        assert expected == actual
