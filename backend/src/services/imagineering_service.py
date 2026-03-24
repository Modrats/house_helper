"""Imagineering service — generates reimagined room images using FLUX.2-pro.

Reads room classifications from outputs/houses/{slug}/room_classifications.json,
generates reimagined images via the FLUX.2-pro API, and writes results to
outputs/houses/{slug}/imagineered/{room_type}/{photo}.png.

Uses exponential backoff for API retries. Idempotent — skips already-generated images.
"""

from __future__ import annotations

import base64
import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from string import Template

import requests

from ..interfaces.imagineering import IImagineeringService
from ..models.imagineering import ImagineeringPhoto, ImagineeringResult

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_MAX_RETRIES = 5
_BASE_DELAY = 2.0
_MAX_DELAY = 120.0
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_REQUEST_TIMEOUT = 300


class FluxImagineeringService(IImagineeringService):
    """Generates reimagined room images via the FLUX.2-pro API.

    Args:
        api_key: Bearer token for the FLUX API.
        endpoint: FLUX.2-pro endpoint URL.
        input_dir: Root directory containing house input data.
        output_dir: Root directory for imagineering output.
        guidance: Guidance scale for image generation.
        default_seed: Default seed for reproducibility (None = random).
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        input_dir: Path,
        output_dir: Path,
        guidance: float,
        default_seed: int | None = None,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._input_dir = input_dir
        self._output_dir = output_dir
        self._guidance = guidance
        self._default_seed = default_seed
        self._prompt_template = Template(
            (_PROMPTS_DIR / "imagineering_prompt.txt").read_text(encoding="utf-8")
        )

    def imagineer_house(self, slug: str) -> ImagineeringResult:
        """Reimagine all classified rooms for a single house.

        Reads room classifications, generates reimagined images for each photo,
        and writes results to the output directory. Skips already-generated images.

        Args:
            slug: House identifier (folder name under input_dir/houses/).

        Returns:
            ImagineeringResult with per-photo generation results.
        """
        classifications = self._load_classifications(slug)
        if not classifications:
            logger.warning("No classifications found for house '%s'", slug)
            return ImagineeringResult(slug=slug)

        results_file = self._output_dir / "houses" / slug / "imagineering_results.json"
        existing = self._load_previous_results(results_file)
        already_done = {p.filename for p in existing}

        to_process = [c for c in classifications if c["filename"] not in already_done]
        if not to_process:
            logger.info(
                "All %d photos already imagineered for '%s'",
                len(classifications),
                slug,
            )
            return ImagineeringResult(slug=slug, photos=existing)

        logger.info(
            "Imagineering %d new photos for '%s' (%d already done)",
            len(to_process),
            slug,
            len(already_done),
        )

        new_photos: list[ImagineeringPhoto] = []
        for entry in to_process:
            photo = self._imagineer_photo(slug, entry)
            if photo is not None:
                new_photos.append(photo)

        all_photos = existing + new_photos
        result = ImagineeringResult(slug=slug, photos=all_photos)
        self._save_results(results_file, result)

        logger.info(
            "Imagineered %d photos for '%s' (%d new)",
            len(all_photos),
            slug,
            len(new_photos),
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_classifications(self, slug: str) -> list[dict]:
        """Load room classifications from the output directory.

        Args:
            slug: House identifier.

        Returns:
            List of classification dicts with filename and room_type keys.
        """
        classifications_file = self._output_dir / "houses" / slug / "room_classifications.json"
        if not classifications_file.exists():
            return []

        try:
            data = json.loads(classifications_file.read_text(encoding="utf-8"))
            return data.get("classifications", [])
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Corrupt classifications file %s: %s", classifications_file, exc)
            return []

    def _imagineer_photo(self, slug: str, classification: dict) -> ImagineeringPhoto | None:
        """Generate a reimagined image for a single photo.

        Args:
            slug: House identifier.
            classification: Dict with filename and room_type.

        Returns:
            ImagineeringPhoto result, or None if the source photo is missing.
        """
        filename = classification["filename"]
        room_type = classification["room_type"]

        source_path = self._input_dir / "houses" / slug / "photos" / filename
        if not source_path.exists():
            logger.warning("Source photo not found: %s", source_path)
            return None

        prompt = self._prompt_template.substitute(room_type=room_type)
        seed = self._default_seed if self._default_seed is not None else random.randint(0, 2**31)

        image_bytes = source_path.read_bytes()
        generated = self._call_flux_api(
            image_bytes=image_bytes,
            prompt=prompt,
            guidance=self._guidance,
            seed=seed,
        )

        output_stem = Path(filename).stem
        output_path = (
            self._output_dir / "houses" / slug / "imagineered" / room_type / f"{output_stem}.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(generated)

        timestamp = datetime.now(timezone.utc).isoformat()
        relative_output = str(output_path.relative_to(self._output_dir))

        logger.info("Generated %s → %s", filename, relative_output)
        return ImagineeringPhoto(
            filename=filename,
            room_type=room_type,
            prompt_used=prompt,
            guidance_value=self._guidance,
            output_path=relative_output,
            timestamp=timestamp,
        )

    def _call_flux_api(
        self,
        *,
        image_bytes: bytes,
        prompt: str,
        guidance: float,
        seed: int,
    ) -> bytes:
        """Call the FLUX.2-pro API with exponential backoff retries.

        Args:
            image_bytes: Raw bytes of the source image.
            prompt: Generation prompt.
            guidance: Guidance scale.
            seed: Random seed for reproducibility.

        Returns:
            Raw PNG bytes of the generated image.

        Raises:
            RuntimeError: If the API call fails after all retries.
        """
        url = f"{self._endpoint}?api-version=preview"
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        body = {
            "prompt": prompt,
            "model": "FLUX.2-pro",
            "n": 1,
            "width": 1024,
            "height": 1024,
            "guidance": guidance,
            "steps": 50,
            "seed": seed,
            "input_image": b64_image,
        }

        last_error: str | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._api_key}",
                    },
                    json=body,
                    timeout=_REQUEST_TIMEOUT,
                )

                if resp.ok:
                    data = resp.json().get("data", [])
                    if not data or "b64_json" not in data[0]:
                        raise RuntimeError(f"Unexpected FLUX response shape: {resp.text[:500]}")
                    return base64.b64decode(data[0]["b64_json"])

                if resp.status_code in _RETRYABLE_STATUS_CODES:
                    delay = min(_BASE_DELAY * (2**attempt), _MAX_DELAY) + random.uniform(0, 1)
                    logger.warning(
                        "FLUX API %d, retrying in %.1fs (attempt %d/%d)",
                        resp.status_code,
                        delay,
                        attempt + 1,
                        _MAX_RETRIES + 1,
                    )
                    time.sleep(delay)
                    last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    continue

                resp.raise_for_status()

            except requests.RequestException as exc:
                if attempt < _MAX_RETRIES:
                    delay = min(_BASE_DELAY * (2**attempt), _MAX_DELAY)
                    logger.warning("FLUX API error: %s — retrying in %.1fs", exc, delay)
                    time.sleep(delay)
                    last_error = str(exc)
                else:
                    raise RuntimeError(
                        f"FLUX request failed after {_MAX_RETRIES + 1} attempts: {exc}"
                    ) from exc

        raise RuntimeError(f"FLUX request failed after {_MAX_RETRIES + 1} attempts: {last_error}")

    @staticmethod
    def _load_previous_results(results_file: Path) -> list[ImagineeringPhoto]:
        """Load previously saved imagineering results for idempotent re-runs.

        Args:
            results_file: Path to the imagineering_results.json file.

        Returns:
            List of previously saved ImagineeringPhoto objects, or empty list.
        """
        if not results_file.exists():
            return []

        try:
            data = json.loads(results_file.read_text(encoding="utf-8"))
            return [ImagineeringPhoto(**entry) for entry in data.get("photos", [])]
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Corrupt imagineering results file %s, re-generating: %s",
                results_file,
                exc,
            )
            return []

    @staticmethod
    def _save_results(results_file: Path, result: ImagineeringResult) -> None:
        """Persist imagineering results to JSON.

        Args:
            results_file: Destination path for imagineering_results.json.
            result: Imagineering results to persist.
        """
        results_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "slug": result.slug,
            "photos": [photo.model_dump() for photo in result.photos],
        }
        results_file.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
