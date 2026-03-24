"""Room classifier service — classifies house photos into room types using a vision LLM.

Reads photos from input_data/houses/{slug}/photos/, sends them to Azure OpenAI
GPT-4V for classification, and writes results to outputs/houses/{slug}/room_classifications.json.

Follows ADR-004: LLM calls are isolated behind a method boundary for VCR-style
test mocking. The _call_vision_model method is the single integration point.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from openai import AzureOpenAI

from ..models.classification import HouseClassifications, PhotoClassification
from ..models.room import RoomType
from ..observability import get_logger, profiled
from ..settings import Settings

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

ROOM_TYPE_VALUES = [rt.value for rt in RoomType]

CLASSIFICATION_PROMPT = (
    "You are a real estate photo classifier. Classify this photo into exactly one room type.\n"
    f"Valid room types: {', '.join(ROOM_TYPE_VALUES)}\n\n"
    "Respond with ONLY a JSON object (no markdown, no extra text):\n"
    '{"room_type": "<type>", "confidence": <0.0-1.0>}\n\n'
    "Rules:\n"
    "- confidence should reflect how clearly the photo shows that room type\n"
    '- Use "unknown" if the photo is too ambiguous to classify\n'
    '- Use "floor_plan" for architectural drawings or floor plans\n'
    '- Use "exterior" for outside views of the whole building\n'
    '- Use "garden" for outdoor garden/yard areas\n'
)

# Process photos in batches of this size to avoid overwhelming the API.
DEFAULT_BATCH_SIZE = 5


class RoomClassifier:
    """Classifies house photos into room types using Azure OpenAI vision.

    Args:
        settings: Application settings with Azure OpenAI credentials.
        input_dir: Root directory containing house folders.
        output_dir: Root directory for classification output.
    """

    def __init__(self, settings: Settings, input_dir: Path, output_dir: Path) -> None:
        settings.require_azure_openai()
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,  # type: ignore[arg-type]
            api_key=settings.azure_openai_api_key,
            api_version="2024-10-21",
        )
        self._deployment = settings.azure_openai_deployment
        self._input_dir = input_dir
        self._output_dir = output_dir

    @profiled
    def classify_house(
        self,
        slug: str,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> HouseClassifications:
        """Classify all photos for a single house, skipping already-classified ones.

        Args:
            slug: House identifier (folder name under input_dir/houses/).
            batch_size: Number of photos to process per batch.

        Returns:
            HouseClassifications with per-photo results.
        """
        photos_dir = self._input_dir / "houses" / slug / "photos"
        output_file = self._output_dir / "houses" / slug / "room_classifications.json"

        if not photos_dir.exists():
            logger.warning("No photos directory for house '%s'", slug)
            return HouseClassifications(slug=slug)

        photo_files = sorted(
            f
            for f in photos_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        if not photo_files:
            logger.info("No photos found for house '%s'", slug)
            return HouseClassifications(slug=slug)

        # Load existing classifications for idempotent re-runs.
        existing = self._load_existing(output_file)
        already_classified = {c.filename for c in existing}

        to_classify = [f for f in photo_files if f.name not in already_classified]
        if not to_classify:
            logger.info("All %d photos already classified for '%s'", len(photo_files), slug)
            return HouseClassifications(slug=slug, classifications=existing)

        logger.info(
            "Classifying %d new photos for '%s' (%d already done)",
            len(to_classify),
            slug,
            len(already_classified),
        )

        new_classifications: list[PhotoClassification] = []
        for i in range(0, len(to_classify), batch_size):
            batch = to_classify[i : i + batch_size]
            logger.debug("Processing batch %d–%d", i + 1, min(i + batch_size, len(to_classify)))
            for photo_path in batch:
                classification = self._classify_single_photo(photo_path)
                new_classifications.append(classification)

        all_classifications = existing + new_classifications
        result = HouseClassifications(slug=slug, classifications=all_classifications)

        self._save_results(output_file, result)
        logger.info(
            "Classified %d photos for '%s' (%d new)",
            len(all_classifications),
            slug,
            len(new_classifications),
        )
        return result

    def _classify_single_photo(self, photo_path: Path) -> PhotoClassification:
        """Classify a single photo by calling the vision model.

        Args:
            photo_path: Absolute path to the photo file.

        Returns:
            PhotoClassification with room type and confidence.
        """
        image_data = base64.b64encode(photo_path.read_bytes()).decode("utf-8")
        media_type = _media_type_for(photo_path.suffix.lower())

        raw_response = self._call_vision_model(image_data, media_type)
        return self._parse_response(photo_path.name, raw_response)

    def _call_vision_model(self, image_b64: str, media_type: str) -> str:
        """Send image to Azure OpenAI vision model and return raw text response.

        This method is the single integration point with the LLM — isolate
        it for VCR-style test mocking per ADR-004.

        Args:
            image_b64: Base64-encoded image data.
            media_type: MIME type of the image (e.g. "image/jpeg").

        Returns:
            Raw text response from the model.
        """
        response = self._client.chat.completions.create(
            model=self._deployment,  # type: ignore[arg-type]
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CLASSIFICATION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=150,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _parse_response(filename: str, raw: str) -> PhotoClassification:
        """Parse LLM response JSON into a PhotoClassification.

        Handles common LLM quirks like markdown code fences and extra text.

        Args:
            filename: Photo filename for the result.
            raw: Raw text response from the vision model.

        Returns:
            PhotoClassification with parsed room type and confidence.
        """
        text = raw.strip()
        # Strip markdown code fences if present.
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [ln for ln in lines if not ln.startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response for '%s': %s", filename, text[:200])
            return PhotoClassification(
                filename=filename,
                room_type=RoomType.UNKNOWN,
                confidence=0.0,
            )

        room_type_str = data.get("room_type", "unknown")
        try:
            room_type = RoomType(room_type_str)
        except ValueError:
            logger.warning(
                "Unknown room type '%s' for '%s', defaulting to UNKNOWN",
                room_type_str,
                filename,
            )
            room_type = RoomType.UNKNOWN

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return PhotoClassification(
            filename=filename,
            room_type=room_type,
            confidence=confidence,
        )

    @staticmethod
    def _load_existing(output_file: Path) -> list[PhotoClassification]:
        """Load previously saved classifications for idempotent re-runs.

        Args:
            output_file: Path to the room_classifications.json file.

        Returns:
            List of previously saved PhotoClassification objects, or empty list.
        """
        if not output_file.exists():
            return []

        try:
            data = json.loads(output_file.read_text(encoding="utf-8"))
            return [
                PhotoClassification(
                    filename=entry["filename"],
                    room_type=RoomType(entry["room_type"]),
                    confidence=float(entry["confidence"]),
                )
                for entry in data.get("classifications", [])
            ]
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Corrupt classifications file %s, re-classifying: %s", output_file, exc)
            return []

    @staticmethod
    def _save_results(output_file: Path, results: HouseClassifications) -> None:
        """Persist classification results to JSON.

        Args:
            output_file: Destination path for room_classifications.json.
            results: Classification results to persist.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "slug": results.slug,
            "classifications": results.to_detailed_dict(),
        }
        output_file.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )


def _media_type_for(suffix: str) -> str:
    """Map a file extension to a MIME type."""
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")
