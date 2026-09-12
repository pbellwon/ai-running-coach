from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkoutExecutionReview:
    session_id: str

    planned_workout_type: str | None
    executed_workout_type: str

    status: str
    confidence: float

    planned_distance_km: float | None
    executed_distance_km: float | None

    planned_duration_min: float | None
    executed_duration_min: float | None

    athlete_feedback: str | None

    evidence: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )