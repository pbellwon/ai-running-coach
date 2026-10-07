
from dataclasses import dataclass, field
from datetime import date
from typing import Literal


AdaptationDecision = Literal[
    "keep_plan",
    "reduce_load",
    "replace_with_easy",
    "manual_review",
]


@dataclass(frozen=True)
class AdaptationProposal:
    """A proposed change to a planned workout, not an applied change."""

    target_date: date
    original_workout_title: str
    original_workout_type: str

    decision: AdaptationDecision

    proposed_workout_type: str | None
    proposed_distance_km: float | None
    proposed_duration_min: int | None

    reason: str
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    requires_athlete_approval: bool = True