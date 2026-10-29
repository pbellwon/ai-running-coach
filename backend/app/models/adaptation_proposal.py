
from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
from typing import Literal


AdaptationDecision = Literal[
    "keep_plan",
    "reduce_load",
    "replace_with_easy",
    "rest",
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

    @property
    def proposal_id(self) -> str:
        """Identify the actionable proposal independently of explanatory text."""
        payload = {
            "target_date": self.target_date.isoformat(),
            "original_workout_title": self.original_workout_title,
            "original_workout_type": self.original_workout_type,
            "decision": self.decision,
            "proposed_workout_type": self.proposed_workout_type,
            "proposed_distance_km": (
                float(self.proposed_distance_km)
                if self.proposed_distance_km is not None else None
            ),
            "proposed_duration_min": self.proposed_duration_min,
            "requires_athlete_approval": self.requires_athlete_approval,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
