"""LLM-based text filter service — evaluates listing text against criteria using AI.

Sends listing text and criteria to an ILLMService for structured evaluation.
Results are cached to outputs/houses/{slug}/text_analysis.json and reused
when the criteria config hasn't changed.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from string import Template
from typing import Any

from pydantic import Field

from ..interfaces.filter import IFilter
from ..interfaces.llm_service import ILLMService
from ..models.house import FilterResult, House
from ..models.llm import LLMResponse
from ..models.text_analysis import CriterionResult, TextAnalysis

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


# ------------------------------------------------------------------
# Internal LLM response models (private to this service)
# ------------------------------------------------------------------


class _CriterionEval(LLMResponse):
    """LLM's evaluation of a single criterion."""

    criterion_name: str
    met: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class _TextAnalysisResult(LLMResponse):
    """Structured-output wrapper returned by the LLM."""

    evaluations: list[_CriterionEval]


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class LLMTextFilterService(IFilter):
    """Filters houses by evaluating listing text against criteria via an LLM.

    Args:
        llm_service: LLM service for structured text completions.
        output_dir: Root directory for cached analysis output.
    """

    def __init__(
        self,
        llm_service: ILLMService,
        output_dir: Path,
    ) -> None:
        self._llm_service = llm_service
        self._output_dir = output_dir
        self._prompt_template = Template(
            (_PROMPTS_DIR / "text_analysis_prompt.txt").read_text(encoding="utf-8")
        )

    @property
    def name(self) -> str:
        return "llm_text_filter"

    def filter(
        self,
        houses: list[House],
        criteria: dict[str, Any],
    ) -> dict[str, FilterResult]:
        """Evaluate houses against criteria using LLM text analysis.

        Args:
            houses: List of houses to evaluate.
            criteria: Criteria dict with p1_criteria, p2_criteria, excluded_criteria.

        Returns:
            Mapping of slug -> FilterResult.
        """
        criteria_hash = _compute_criteria_hash(criteria)
        all_criteria = _build_criteria_list(criteria)

        results: dict[str, FilterResult] = {}
        for house in houses:
            analysis = self._analyze_house(house, all_criteria, criteria_hash)
            results[house.slug] = analysis.to_filter_result()
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _analyze_house(
        self,
        house: House,
        all_criteria: list[tuple[str, str]],
        criteria_hash: str,
    ) -> TextAnalysis:
        """Analyze a single house, using cache when criteria are unchanged."""
        output_file = self._output_dir / house.slug / "text_analysis.json"

        cached = self._load_cached(output_file, criteria_hash)
        if cached is not None:
            logger.info("Using cached text analysis for '%s'", house.slug)
            return cached

        logger.info("Running LLM text analysis for '%s'", house.slug)
        analysis = self._run_llm_analysis(house, all_criteria, criteria_hash)
        self._save_results(output_file, analysis)
        return analysis

    def _load_cached(
        self,
        output_file: Path,
        criteria_hash: str,
    ) -> TextAnalysis | None:
        """Load cached analysis if it exists and criteria haven't changed."""
        if not output_file.exists():
            return None

        try:
            data = json.loads(output_file.read_text(encoding="utf-8"))
            analysis = TextAnalysis(**data)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Corrupt cache file %s, will re-analyze", output_file)
            return None

        if analysis.criteria_hash != criteria_hash:
            logger.info("Criteria changed for '%s', will re-analyze", analysis.slug)
            return None

        return analysis

    def _run_llm_analysis(
        self,
        house: House,
        all_criteria: list[tuple[str, str]],
        criteria_hash: str,
    ) -> TextAnalysis:
        """Send listing text + criteria to the LLM and parse the response."""
        criteria_text = "\n".join(
            f"- [{category}] {criterion}" for criterion, category in all_criteria
        )
        prompt = self._prompt_template.substitute(
            listing_text=house.listing_text,
            criteria_list=criteria_text,
        )

        response = self._llm_service.complete_structured(prompt, _TextAnalysisResult)
        assert isinstance(response, _TextAnalysisResult)

        evaluations = [
            CriterionResult(
                criterion_name=ev.criterion_name,
                category=self._resolve_category(ev.criterion_name, all_criteria),
                met=ev.met,
                confidence=ev.confidence,
                reasoning=ev.reasoning,
            )
            for ev in response.evaluations
        ]

        return TextAnalysis(
            slug=house.slug,
            criteria_hash=criteria_hash,
            evaluations=evaluations,
        )

    def _resolve_category(
        self,
        criterion_name: str,
        all_criteria: list[tuple[str, str]],
    ) -> str:
        """Look up the category for a criterion name from the criteria list."""
        for criterion, category in all_criteria:
            if criterion == criterion_name:
                return category
        logger.warning(
            "LLM returned unknown criterion '%s', defaulting to 'p2'",
            criterion_name,
        )
        return "p2"

    def _save_results(self, output_file: Path, analysis: TextAnalysis) -> None:
        """Write analysis to JSON cache file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(analysis.model_dump(), indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("Saved text analysis to %s", output_file)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _compute_criteria_hash(criteria: dict[str, Any]) -> str:
    """Compute a stable SHA-256 hash of the criteria dict."""
    canonical = json.dumps(criteria, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _build_criteria_list(criteria: dict[str, Any]) -> list[tuple[str, str]]:
    """Build a flat list of (criterion_text, category) tuples from criteria config."""
    result: list[tuple[str, str]] = []
    for criterion in criteria.get("p1_criteria", []):
        result.append((criterion, "p1"))
    for criterion in criteria.get("p2_criteria", []):
        result.append((criterion, "p2"))
    for criterion in criteria.get("excluded_criteria", []):
        result.append((criterion, "excluded"))
    return result
