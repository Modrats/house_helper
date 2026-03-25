"""Photo criteria checker service — evaluates room photos for required visual features.

Reads room classifications from outputs/houses/{slug}/room_classifications.json,
looks up criteria per room type, sends each photo + criteria prompt to an ILLMService,
and writes results to outputs/houses/{slug}/photo_criteria.json.

Uses structured output via ILLMService — no manual JSON parsing needed.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from pathlib import Path
from string import Template

from pydantic import Field

from ..interfaces.llm_service import ILLMService
from ..interfaces.photo_checker import IPhotoChecker
from ..models.llm import LLMResponse
from ..models.photo_criteria import (
    FeatureCheck,
    PhotoCriteriaResult,
    RoomCriteriaResult,
)
from ..models.room import RoomType

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class _FeatureEval(LLMResponse):
    """LLM evaluation of a single visual feature."""

    feature_name: str
    present: bool
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str


class _PhotoCheckResult(LLMResponse):
    """Structured-output wrapper for the LLM's feature evaluation response."""

    features: list[_FeatureEval]


class VisionPhotoChecker(IPhotoChecker):
    """Checks room photos against visual criteria via a vision LLM.

    Args:
        llm_service: LLM service for vision evaluation calls.
        input_dir: Root directory containing house photo folders.
        output_dir: Root directory for checker output.
        criteria: Room-type-keyed criteria config mapping room types to
            ``{"required": [...], "preferred": [...]}``.
    """

    def __init__(
        self,
        llm_service: ILLMService,
        input_dir: Path,
        output_dir: Path,
        criteria: dict[str, dict[str, list[str]]],
    ) -> None:
        self._llm_service = llm_service
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._criteria = criteria
        self._prompt_template = Template(
            (_PROMPTS_DIR / "photo_criteria_prompt.txt").read_text(encoding="utf-8")
        )

    def check_house(self, slug: str) -> PhotoCriteriaResult:
        """Check all classified rooms in a house against photo criteria.

        Reads ``room_classifications.json`` to determine which room type
        each photo belongs to, then evaluates each photo against the
        configured criteria for that room type.

        Args:
            slug: House identifier (folder name under input_dir/houses/).

        Returns:
            PhotoCriteriaResult with per-room feature evaluations.
        """
        classifications = self._load_classifications(slug)
        if not classifications:
            logger.info("No classifications found for '%s', nothing to check", slug)
            return PhotoCriteriaResult(slug=slug)

        output_file = self._output_dir / slug / "photo_criteria.json"
        criteria_hash = self._hash_criteria()
        existing = self._load_previous_results(output_file, criteria_hash)
        already_checked = {r.photo_filename for r in existing}

        to_check = [c for c in classifications if c["filename"] not in already_checked]
        if not to_check:
            logger.info(
                "All %d photos already checked for '%s'",
                len(classifications),
                slug,
            )
            return PhotoCriteriaResult(slug=slug, room_results=existing)

        logger.info(
            "Checking %d new photos for '%s' (%d already done)",
            len(to_check),
            slug,
            len(already_checked),
        )

        new_results: list[RoomCriteriaResult] = []
        for entry in to_check:
            result = self._check_photo(slug, entry)
            if result is not None:
                new_results.append(result)

        all_results = existing + new_results
        house_result = PhotoCriteriaResult(slug=slug, room_results=all_results)

        self._save_results(output_file, house_result, criteria_hash)
        logger.info(
            "Checked %d photos for '%s' (%d new)",
            len(all_results),
            slug,
            len(new_results),
        )
        return house_result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_classifications(self, slug: str) -> list[dict[str, str | float]]:
        """Load room classifications for a house.

        Args:
            slug: House identifier.

        Returns:
            List of classification dicts with filename, room_type, confidence.
            Empty list if the classifications file is missing or corrupt.
        """
        classifications_file = self._output_dir / slug / "room_classifications.json"
        if not classifications_file.exists():
            logger.warning("No room_classifications.json for house '%s'", slug)
            return []

        try:
            data = json.loads(classifications_file.read_text(encoding="utf-8"))
            return data.get("classifications", [])
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Corrupt classifications file %s: %s",
                classifications_file,
                exc,
            )
            return []

    def _check_photo(
        self, slug: str, classification: dict[str, str | float]
    ) -> RoomCriteriaResult | None:
        """Check a single photo against criteria for its room type.

        Args:
            slug: House identifier.
            classification: Dict with filename, room_type, confidence.

        Returns:
            RoomCriteriaResult, or None if the photo file is missing or
            the room type has no configured criteria.
        """
        filename = str(classification["filename"])
        room_type_str = str(classification["room_type"])

        try:
            room_type = RoomType(room_type_str)
        except ValueError:
            logger.warning(
                "Unknown room type '%s' for photo '%s', skipping",
                room_type_str,
                filename,
            )
            return None

        room_criteria = self._criteria.get(room_type_str)
        if room_criteria is None:
            logger.info(
                "No criteria configured for room type '%s', skipping '%s'",
                room_type_str,
                filename,
            )
            return None

        required = room_criteria.get("required", [])
        preferred = room_criteria.get("preferred", [])
        all_features = required + preferred

        if not all_features:
            return RoomCriteriaResult(
                room_type=room_type,
                photo_filename=filename,
            )

        photo_path = self._find_photo(slug, filename)
        if photo_path is None:
            logger.warning("Photo file not found for '%s' in house '%s'", filename, slug)
            return None

        image_data = base64.b64encode(photo_path.read_bytes()).decode("utf-8")
        media_type = _media_type_for(photo_path.suffix.lower())

        feature_list_str = "\n".join(f"- {f}" for f in all_features)
        prompt = self._prompt_template.substitute(
            room_type=room_type_str,
            feature_list=feature_list_str,
        )

        resp = self._llm_service.classify_image(
            prompt=prompt,
            image_b64=image_data,
            media_type=media_type,
            response_model=_PhotoCheckResult,
        )

        eval_map = {e.feature_name: e for e in resp.features}
        required_checks = _build_checks(required, eval_map)
        preferred_checks = _build_checks(preferred, eval_map)

        return RoomCriteriaResult(
            room_type=room_type,
            photo_filename=filename,
            required_features=required_checks,
            preferred_features=preferred_checks,
        )

    def _find_photo(self, slug: str, filename: str) -> Path | None:
        """Locate a photo file in the house's photo directory.

        Args:
            slug: House identifier.
            filename: Photo filename to find.

        Returns:
            Path to the photo, or None if not found.
        """
        photo_path = self._input_dir / slug / "photos" / filename
        if photo_path.is_file():
            return photo_path
        return None

    def _hash_criteria(self) -> str:
        """Return a short hash of the current photo criteria for drift detection."""
        blob = json.dumps(self._criteria, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]

    @staticmethod
    def _load_previous_results(
        output_file: Path,
        criteria_hash: str | None = None,
    ) -> list[RoomCriteriaResult]:
        """Load previously saved criteria results for idempotent re-runs.

        Returns an empty list (forcing a full re-check) if the file is missing,
        corrupt, or was generated with different criteria.
        """
        if not output_file.exists():
            return []

        try:
            data = json.loads(output_file.read_text(encoding="utf-8"))
            if criteria_hash and data.get("criteria_hash") != criteria_hash:
                logger.info(
                    "Photo criteria changed for %s — re-checking all photos",
                    output_file.parent.name,
                )
                return []
            results = []
            for entry in data.get("room_results", []):
                results.append(
                    RoomCriteriaResult(
                        room_type=RoomType(entry["room_type"]),
                        photo_filename=entry["photo_filename"],
                        required_features=[
                            FeatureCheck(**f) for f in entry.get("required_features", [])
                        ],
                        preferred_features=[
                            FeatureCheck(**f) for f in entry.get("preferred_features", [])
                        ],
                    )
                )
            return results
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Corrupt photo criteria file %s, re-checking: %s",
                output_file,
                exc,
            )
            return []

    @staticmethod
    def _save_results(
        output_file: Path, results: PhotoCriteriaResult, criteria_hash: str | None = None
    ) -> None:
        """Persist criteria check results to JSON.

        Args:
            output_file: Destination path for photo_criteria.json.
            results: Criteria results to persist.
            criteria_hash: Hash of the criteria used, for drift detection.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "slug": results.slug,
            "criteria_hash": criteria_hash,
            "room_results": results.to_detailed_dict(),
        }
        output_file.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )


def _build_checks(
    feature_names: list[str],
    eval_map: dict[str, _FeatureEval],
) -> list[FeatureCheck]:
    """Build FeatureCheck list from LLM evaluations.

    Features not returned by the LLM are treated as not present.

    Args:
        feature_names: Expected feature names.
        eval_map: LLM evaluation results keyed by feature name.

    Returns:
        List of FeatureCheck objects.
    """
    checks = []
    for name in feature_names:
        evaluation = eval_map.get(name)
        if evaluation is not None:
            checks.append(
                FeatureCheck(
                    feature_name=name,
                    present=evaluation.present,
                    confidence=evaluation.confidence,
                    notes=evaluation.notes,
                )
            )
        else:
            checks.append(
                FeatureCheck(
                    feature_name=name,
                    present=False,
                    confidence=0.0,
                    notes="Feature not evaluated by LLM",
                )
            )
    return checks


def _media_type_for(suffix: str) -> str:
    """Map a file extension to a MIME type."""
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")
