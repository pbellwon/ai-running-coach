from __future__ import annotations

from datetime import date

from app.engine.existing_plan_importer import ExistingPlanImporter
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.models.pacemind_today import (
    PaceMindToday,
    PlannedWorkoutSummary,
)
from app.services.plan_matcher import PlanMatcher
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
    - detect whether today's planned workout is already completed
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

        if self._is_planned_workout_completed(
            planned=planned,
            training_context=training_context,
        ):
            last_session = training_context.last_session

            executed_summary = (
                f"Completed: "
                f"{last_session.distance_km:.2f} km"
                if (
                    last_session is not None
                    and last_session.distance_km is not None
                )
                else "Planned workout already completed."
            )

            return PaceMindToday(
                target_date=target_date,
                planned_workout=planned_summary,
                recovery=recovery,
                recovery_trend=recovery_trend,
                training_context=training_context,
                decision=None,
                recommendation=None,
                status="completed",
                message=executed_summary,
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

    def _is_planned_workout_completed(
        self,
        planned,
        training_context,
    ) -> bool:

        last_session = training_context.last_session

        if last_session is None:
            return False

        matched = PlanMatcher().match(
            executed_workout=last_session,
            planned_workouts=[planned],
        )

        if matched is None:
            return False

        return self._execution_matches_plan(
            planned=planned,
            executed=last_session,
        )

    def _execution_matches_plan(
        self,
        planned,
        executed,
    ) -> bool:

        planned_type = planned.workout_type
        executed_type = executed.workout_type

        running_types = {
            "easy_run",
            "easy_run+strides",
            "easy_run+hills",
            "threshold",
            "tempo_run",
            "vo2max",
            "long_run",
            "long_run+progression",
            "race",
        }

        if planned_type in {
            "long_run",
            "long_run+progression",
        }:
            if executed.sport_family != "running":
                return False

            if (
                planned.planned_distance_km is not None
                and executed.distance_km is not None
            ):
                minimum_distance = (
                    planned.planned_distance_km * 0.70
                )

                return (
                    executed.distance_km
                    >= minimum_distance
                )

            return True

        if planned_type in running_types:
            if executed.sport_family != "running":
                return False

            if planned_type == executed_type:
                return True

            compatible_running_types = {
                ("easy_run", "easy_run+strides"),
                ("easy_run+strides", "easy_run"),
                ("tempo_run", "threshold"),
                ("threshold", "tempo_run"),
            }

            return (
                planned_type,
                executed_type,
            ) in compatible_running_types

        if planned_type == "strength":
            return executed_type == "strength"

        if planned_type == "bike":
            return executed_type == "bike"

        return planned_type == executed_type