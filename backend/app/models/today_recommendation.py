from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TodayRecommendation:
    decision: str

    recommendation_type: str

    original_workout_type: str | None
    recommended_workout_type: str | None

    original_distance_km: float | None
    recommended_distance_km: float | None

    original_duration_min: int | None
    recommended_duration_min: int | None

    title: str
    summary: str

    reasons: list[str]
    warnings: list[str]