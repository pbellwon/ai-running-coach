from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkoutExplanation:
    """
    Deterministic explainability contract for a completed workout.

    Distinguishes:
    - planned session intent;
    - executed workout profile;
    - execution structure;
    - athlete feedback;
    - execution-review evidence and warnings.

    The LLM layer may interpret this structure, but it must not
    replace or override the deterministic review.
    """

    session_id: str
    target_date: str

    status: str
    confidence: float

    planned_workout: dict[str, Any] | None
    executed_workout: dict[str, Any]

    athlete_feedback: Any | None

    key_evidence: list[str]
    warnings: list[str]
    uncertainties: list[str]

    context: dict[str, Any]

    execution_structure: dict[str, Any] | None = None