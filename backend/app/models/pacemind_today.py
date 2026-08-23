from __future__ import annotations

from dataclasses import dataclass

from app.models.recovery_snapshot import RecoverySnapshot
from app.models.recovery_trend import RecoveryTrend
from app.models.training_context import TrainingContext
from app.models.training_decision import TrainingDecision
from app.models.today_recommendation import TodayRecommendation


@dataclass
class PlannedWorkoutSummary:
    title: str
    workout_type: str | None
    description: str | None
    planned_distance_km: float | None
    planned_duration_min: int | None
    priority: str | None


@dataclass
class PaceMindToday:
    target_date: str

    planned_workout: PlannedWorkoutSummary | None

    recovery: RecoverySnapshot | None
    recovery_trend: RecoveryTrend | None
    training_context: TrainingContext | None

    decision: TrainingDecision | None
    recommendation: TodayRecommendation | None

    status: str
    message: str | None