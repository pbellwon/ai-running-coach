from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TodayExplanation:
    """
    Deterministic explanation contract for today's
    PaceMind recommendation.

    This object contains structured evidence that can
    later be passed to an LLM for natural-language
    explanation.
    """

    target_date: str

    status: str

    decision: str | None
    recommendation_type: str | None

    confidence: float | None

    key_reasons: list[str]
    warnings: list[str]
    uncertainties: list[str]

    context: dict[str, Any]