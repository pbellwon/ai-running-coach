from __future__ import annotations

from datetime import date

from app.engine.existing_plan_importer import ExistingPlanImporter
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.models.pacemind_today import (
    PaceMindToday,
    PlannedWorkoutSummary,
)
from app.services.recovery_snapshot_service import RecoverySnapshotService
from app.services.recovery_trend_service import RecoveryTrendService
from app.services.today_recommendation_service import (
    TodayRecommendationService,
)
from app.services.training_context_service import TrainingContextService
from app.services.training_decision_engine import TrainingDecisionEngine


class PaceMindTodayService:
    """
    Orchestrates all data needed for the PaceMind Today response.

    Responsibilities:
    - load today's planned workout
    - build recovery snapshot
    - build recovery trend
    - build training context
    - make training decision
    - create concrete recommendation
    """

    def build(
        self,
        target_date: str,
    ) -> PaceMindToday:

        normalized_date = date.fromisoformat(
            target_date
        )

        planned = self._get_planned_workout(
            normalized_date
        )

        if planned is None:
            return PaceMindToday(
                target_date=target_date,
                planned_workout=None,
                recovery=None,
                recovery_trend=None,
                training_context=None,
                decision=None,
                recommendation=None,
                status="no_planned_workout",
                message=(
                    "No planned workout found "
                    "for this date."
                ),
            )

        recovery = (
            RecoverySnapshotService()
            .build(target_date)
        )

        recovery_trend = (
            RecoveryTrendService()
            .build(target_date)
        )

        training_context = (
            TrainingContextService()
            .build(target_date)
        )

        planned_session_role = (
            "long_run"
            if planned.workout_type
            in {
                "long_run",
                "long_run+progression",
            }
            else None
        )

        decision = (
            TrainingDecisionEngine()
            .decide(
                recovery=recovery,
                trend=recovery_trend,
                training_context=training_context,
                planned_workout_type=(
                    planned.workout_type
                ),
                planned_session_role=(
                    planned_session_role
                ),
            )
        )

        recommendation = (
            TodayRecommendationService()
            .build(
                decision=decision,
                planned_title=planned.title,
                planned_workout_type=(
                    planned.workout_type
                ),
                planned_distance_km=(
                    planned.planned_distance_km
                ),
                planned_duration_min=(
                    planned.planned_duration_min
                ),
            )
        )

        planned_summary = PlannedWorkoutSummary(
            title=planned.title,
            workout_type=planned.workout_type,
            description=planned.description,
            planned_distance_km=(
                planned.planned_distance_km
            ),
            planned_duration_min=(
                planned.planned_duration_min
            ),
            priority=planned.priority,
        )

        return PaceMindToday(
            target_date=target_date,
            planned_workout=planned_summary,
            recovery=recovery,
            recovery_trend=recovery_trend,
            training_context=training_context,
            decision=decision,
            recommendation=recommendation,
            status="ready",
            message=None,
        )

    def _get_planned_workout(
        self,
        target_date: date,
    ):
        rows = (
            GoogleSheetsPlanSource()
            .fetch_rows()
        )

        planned_workouts = (
            ExistingPlanImporter()
            .import_rows(rows)
        )

        planned_for_day = [
            workout
            for workout in planned_workouts
            if (
                workout.planned_date
                == target_date
                and workout.workout_type
                != "off"
            )
        ]

        if not planned_for_day:
            return None

        return planned_for_day[0]