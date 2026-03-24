"""Room classifier service — classifies house photos into room types using a vision LLM.

Reads photos from input_data/houses/{slug}/photos/, sends them to an ILLMService
for classification, and writes results to outputs/houses/{slug}/room_classifications.json.

Uses structured output via ILLMService — no manual JSON parsing needed.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from string import Template

from pydantic import Field

from ..interfaces.llm_service import ILLMService
from ..interfaces.room_classifier import IRoomClassifier
from ..models.classification import HouseClassifications, PhotoClassification
from ..models.llm import LLMResponse
from ..models.room import RoomType

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

ROOM_TYPE_VALUES = [rt.value for rt in RoomType]

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class _ClassificationItem(LLMResponse):
    """Single-image entry in the classification prompt response."""

    label: str
    room_type: RoomType
    confidence: float = Field(ge=0.0, le=1.0)
    description: str
    group_id: int


class _ClassificationResult(LLMResponse):
    """Structured-output wrapper returned by the LLM for one batch call."""

    results: list[_ClassificationItem]


class AzureOpenAIRoomClassifier(IRoomClassifier):
    """Classifies house photos into room types via an ILLMService.

    Args:
        llm_service: LLM service for vision classification calls.
        input_dir: Root directory containing house folders.
        output_dir: Root directory for classification output.
        batch_size: Number of photos to process per batch.
    """

    def __init__(
        self,
        llm_service: ILLMService,
        input_dir: Path,
        output_dir: Path,
        batch_size: int,
    ) -> None:
        self._llm_service = llm_service
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._batch_size = batch_size
        self._prompt_template = Template(
            (_PROMPTS_DIR / "classification_prompt.txt").read_text(encoding="utf-8")
        )

    def classify_house(self, slug: str, *, batch_size: int = 0) -> HouseClassifications:
        """Classify all photos for a single house, skipping already-classified ones.

        Args:
            slug: House identifier (folder name under input_dir/houses/).
            batch_size: Override batch size (0 uses the instance default).

        Returns:
            HouseClassifications with per-photo results.
        """
        effective_batch_size = batch_size if batch_size > 0 else self._batch_size
        photos = self._discover_photos(slug)
        output_file = self._output_dir / "houses" / slug / "room_classifications.json"

        if not photos:
            return HouseClassifications(slug=slug)

        existing = self._load_previous_results(output_file)
        already_classified = {c.filename for c in existing}

        to_classify = [f for f in photos if f.name not in already_classified]
        if not to_classify:
            logger.info("All %d photos already classified for '%s'", len(photos), slug)
            return HouseClassifications(slug=slug, classifications=existing)

        logger.info(
            "Classifying %d new photos for '%s' (%d already done)",
            len(to_classify),
            slug,
            len(already_classified),
        )

        new_classifications: list[PhotoClassification] = []
        for i in range(0, len(to_classify), effective_batch_size):
            batch = to_classify[i : i + effective_batch_size]
            new_classifications.extend(self._classify_batch(batch))

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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover_photos(self, slug: str) -> list[Path]:
        """Scan the photo directory for supported image files.

        Args:
            slug: House identifier.

        Returns:
            Sorted list of photo paths, or empty list if dir missing.
        """
        photos_dir = self._input_dir / "houses" / slug / "photos"
        if not photos_dir.exists():
            logger.warning("No photos directory for house '%s'", slug)
            return []

        photos = sorted(
            f
            for f in photos_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not photos:
            logger.info("No photos found for house '%s'", slug)
        return photos

    def _classify_batch(self, photos: list[Path]) -> list[PhotoClassification]:
        """Classify a batch of photos via the LLM service.

        Args:
            photos: Photo file paths to classify.

        Returns:
            List of PhotoClassification results.
        """
        results: list[PhotoClassification] = []
        room_types_str = ", ".join(ROOM_TYPE_VALUES)

        for photo_path in photos:
            image_data = base64.b64encode(photo_path.read_bytes()).decode("utf-8")
            media_type = _media_type_for(photo_path.suffix.lower())
            prompt = self._prompt_template.substitute(
                n_images=1,
                image_labels="image_1",
                room_types=room_types_str,
            )

            resp = self._llm_service.classify_image(
                prompt=prompt,
                image_b64=image_data,
                media_type=media_type,
                response_model=_ClassificationResult,
            )
            if resp.results:
                item = resp.results[0]
                results.append(
                    PhotoClassification(
                        filename=photo_path.name,
                        room_type=item.room_type,
                        confidence=item.confidence,
                    )
                )
        return results

    @staticmethod
    def _load_previous_results(output_file: Path) -> list[PhotoClassification]:
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
