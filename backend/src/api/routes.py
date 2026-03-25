"""API route definitions.

All endpoints are defined here and registered via the router.
Dependencies are injected through FastAPI's Depends mechanism,
wired to the composition root in core.py.

Photos are served through dedicated endpoints rather than static
directory mounts. This means only HouseRepository changes if the
backing storage changes (e.g. from local filesystem to Azure Blob).
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..core import create_repository
from ..observability import get_logger
from ..services.house_repository import HouseRepository
from .models import (
    FilterResultResponse,
    HealthResponse,
    HouseDetailResponse,
    HouseListItemResponse,
    PhotoResponse,
    RoomClassificationResponse,
)

logger = get_logger(__name__)

router = APIRouter()


def get_repo() -> HouseRepository:
    """Dependency provider for HouseRepository — delegates to the composition root."""
    return create_repository()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse()


@router.get("/api/houses", response_model=list[HouseListItemResponse], tags=["houses"])
def list_houses(repo: HouseRepository = Depends(get_repo)) -> list[HouseListItemResponse]:
    """List all houses with summary info."""
    slugs = repo.list_houses()
    items: list[HouseListItemResponse] = []
    for slug in slugs:
        try:
            house = repo.get_house(slug)
        except FileNotFoundError:
            logger.warning("House '%s' listed but not loadable, skipping", slug)
            continue

        photos = repo.get_photos(slug)
        first_photo = house.photos[0].filename if house.photos else None
        thumbnail_url = f"/api/houses/{slug}/photos/{first_photo}" if first_photo else None

        items.append(
            HouseListItemResponse(
                slug=house.slug,
                photo_count=len(photos),
                status=house.status.value,
                has_filter_results=bool(
                    house.filter_results.p1
                    or house.filter_results.p2
                    or house.filter_results.excluded
                ),
                thumbnail_url=thumbnail_url,
            )
        )
    return items


@router.get("/api/houses/{slug}", response_model=HouseDetailResponse, tags=["houses"])
def get_house(slug: str, repo: HouseRepository = Depends(get_repo)) -> HouseDetailResponse:
    """Get full house details including listing text and filter results."""
    try:
        house = repo.get_house(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"House '{slug}' not found")

    filter_results = repo.get_criteria_results(slug)
    room_classifications = repo.get_room_classifications(slug)

    photo_responses = [
        PhotoResponse(
            filename=photo.filename,
            url=f"/api/houses/{slug}/photos/{photo.filename}",
            room_type=_find_room_type(photo.filename, room_classifications),
        )
        for photo in house.photos
    ]

    return HouseDetailResponse(
        slug=house.slug,
        listing_text=house.listing_text,
        status=house.status.value,
        photo_count=len(house.photos),
        room_count=len(room_classifications),
        filter_results=FilterResultResponse(
            p1=filter_results.p1,
            p2=filter_results.p2,
            excluded=filter_results.excluded,
            passed=filter_results.passed,
        ),
        photos=photo_responses,
    )


@router.get(
    "/api/houses/{slug}/rooms",
    response_model=list[RoomClassificationResponse],
    tags=["houses"],
)
def get_room_classifications(
    slug: str, repo: HouseRepository = Depends(get_repo)
) -> list[RoomClassificationResponse]:
    """Get room classifications for a house."""
    try:
        repo.get_house(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"House '{slug}' not found")

    classifications = repo.get_room_classifications(slug)
    return [
        RoomClassificationResponse(
            room_type=room_type,
            display_name=room_type.replace("_", " ").title(),
            photo_count=len(filenames),
            photos=filenames,
        )
        for room_type, filenames in sorted(classifications.items())
    ]


@router.get("/api/houses/{slug}/photos", response_model=list[PhotoResponse], tags=["houses"])
def get_photos(
    slug: str,
    room_type: str | None = Query(default=None),
    repo: HouseRepository = Depends(get_repo),
) -> list[PhotoResponse]:
    """Get photos for a house with optional room type filter."""
    try:
        house = repo.get_house(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"House '{slug}' not found")

    room_classifications = repo.get_room_classifications(slug)
    imagineered = repo.get_imagineered_photos(slug)
    imagineered_names = {_path_to_filename(p) for p in imagineered}

    photos: list[PhotoResponse] = []
    for photo in house.photos:
        photo_room = _find_room_type(photo.filename, room_classifications)
        if room_type and photo_room != room_type:
            continue

        imagineered_url = None
        if photo.filename in imagineered_names:
            imagineered_url = f"/api/houses/{slug}/imagineered/{photo.filename}"

        photos.append(
            PhotoResponse(
                filename=photo.filename,
                url=f"/api/houses/{slug}/photos/{photo.filename}",
                room_type=photo_room,
                imagineered_url=imagineered_url,
            )
        )
    return photos


@router.get("/api/houses/{slug}/photos/{filename}", tags=["photos"])
def get_photo(
    slug: str,
    filename: str,
    repo: HouseRepository = Depends(get_repo),
) -> Response:
    """Serve an input photo for a house.

    Reads the photo bytes through the storage service so switching
    to a cloud backend (e.g. Azure Blob) only requires updating
    HouseRepository — the route stays unchanged.
    """
    try:
        data = repo.get_photo_bytes(slug, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Photo '{filename}' not found")

    media_type, _ = mimetypes.guess_type(filename)
    return Response(content=data, media_type=media_type or "application/octet-stream")


@router.get("/api/houses/{slug}/imagineered/{filename}", tags=["photos"])
def get_imagineered_photo(
    slug: str,
    filename: str,
    repo: HouseRepository = Depends(get_repo),
) -> Response:
    """Serve an imagineered (AI-reimagined) output photo for a house.

    Reads the photo bytes through the storage service so switching
    to a cloud backend only requires updating HouseRepository.
    """
    try:
        data = repo.get_imagineered_photo_bytes(slug, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Imagineered photo '{filename}' not found")

    media_type, _ = mimetypes.guess_type(filename)
    return Response(content=data, media_type=media_type or "application/octet-stream")


def _find_room_type(filename: str, classifications: dict[str, list[str]]) -> str | None:
    """Look up which room type a photo belongs to."""
    for room_type, filenames in classifications.items():
        if filename in filenames:
            return room_type
    return None


def _path_to_filename(path: str) -> str:
    """Extract filename from a full path."""
    return path.rsplit("/", 1)[-1] if "/" in path else path
