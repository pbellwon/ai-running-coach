from __future__ import annotations

from datetime import date, timedelta

from app.engine.existing_plan_importer import ExistingPlanImporter
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource
from app.models.adaptation_proposal import AdaptationProposal
from app.services.recent_execution_review_service import (
    RecentExecutionReviewService,
)
from app.services.recovery_snapshot_service import RecoverySnapshotService
from app.services.recovery_trend_service import RecoveryTrendService
from app.services.today_recommendation_service import (
    TodayRecommendationService,
)
from app.services.training_context_service import TrainingContextService
from app.services.training_decision_engine import TrainingDecisionEngine


class AdaptivePlanningService:
    """
    Builds an adaptation proposal for one planned workout.

    The service does not modify the training plan.
    It only produces a proposal that may later be accepted
    or rejected by the athlete.
    """

    RECENT_REVIEW_LIMIT = 3

    def __init__(
        self,
        plan_source=None,
        plan_importer=None,
        recovery_service=None,
        recovery_trend_service=None,
        training_context_service=None,
        training_decision_engine=None,
        recommendation_service=None,
        recent_review_service=None,
    ):
        self.plan_source = (
            plan_source
            if plan_source is not None
            else GoogleSheetsPlanSource()
        )

        self.plan_importer = (
            plan_importer
            if plan_importer is not None
            else ExistingPlanImporter()
        )

        self.recovery_service = (
            recovery_service
            if recovery_service is not None
            else RecoverySnapshotService()
        )

        self.recovery_trend_service = (
            recovery_trend_service
            if recovery_trend_service is not None
            else RecoveryTrendService()
        )

        self.training_context_service = (
            training_context_service
            if training_context_service is not None
            else TrainingContextService()
        )

        self.training_decision_engine = (
            training_decision_engine
            if training_decision_engine is not None
            else TrainingDecisionEngine()
        )

        self.recommendation_service = (
            recommendation_service
            if recommendation_service is not None
            else TodayRecommendationService()
        )

        self.recent_review_service = (
            recent_review_service
            if recent_review_service is not None
            else RecentExecutionReviewService()
        )

    def build(
        self,
        target_date: str | date,
    ) -> AdaptationProposal | None:
        normalized_date = self._normalize_date(
            target_date
        )

        evaluation_date = min(
            normalized_date,
            date.today(),
        )

        evaluation_date_string = (
            evaluation_date.isoformat()
        )

        planned = self._get_planned_workout(
            normalized_date
        )

        if planned is None:
            return None

        recovery = (
            self.recovery_service
            .build(evaluation_date_string)
        )

        recovery_trend = (
            self.recovery_trend_service
            .build(evaluation_date_string)
        )

        training_context = (
            self.training_context_service
            .build(evaluation_date_string)
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

        training_decision = (
            self.training_decision_engine
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
            self.recommendation_service
            .build(
                decision=training_decision,
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

        recent_reviews = (
            self.recent_review_service
            .build(
                target_date=evaluation_date,
                limit=self.RECENT_REVIEW_LIMIT,
            )
        )

        return self._build_proposal(
            planned=planned,
            recommendation=recommendation,
            training_decision=training_decision,
            recent_reviews=recent_reviews,
        )

    def _build_proposal(
        self,
        planned,
        recommendation,
        training_decision,
        recent_reviews: list[dict],
    ) -> AdaptationProposal:
        decision_map = {
            "as_planned": "keep_plan",
            "reduced": "reduce_load",
            "easy_replacement": (
                "replace_with_easy"
            ),
            "rest": "rest",
        }

        adaptation_decision = (
            decision_map.get(
                recommendation.recommendation_type
            )
        )

        if adaptation_decision is None:
            raise ValueError(
                "Unsupported recommendation type: "
                f"{recommendation.recommendation_type}"
            )

        evidence = list(
            training_decision.reasons
        )

        for review_item in recent_reviews:
            review = (
                review_item.get("review")
                or {}
            )

            evidence.append(
                f"Recent session "
                f"{review_item.get('date', 'unknown')}: "
                f"status="
                f"{review.get('status', 'unknown')}, "
                f"confidence="
                f"{review.get('confidence', 'unknown')}."
            )

        warnings = list(
            training_decision.warnings
        )

        hard_sessions = [
            item
            for item in recent_reviews
            if (
                (
                    item.get("review")
                    or {}
                ).get("status")
                == "too_hard"
                and (
                    (
                        item.get("review")
                        or {}
                    ).get("confidence")
                    or 0
                )
                >= 0.5
            )
        ]

        if (
            len(hard_sessions) >= 2
            and adaptation_decision
            == "keep_plan"
        ):
            return AdaptationProposal(
                target_date=planned.planned_date,
                original_workout_title=(
                    planned.title
                ),
                original_workout_type=(
                    planned.workout_type
                ),
                decision="manual_review",
                proposed_workout_type=(
                    planned.workout_type
                ),
                proposed_distance_km=(
                    planned.planned_distance_km
                ),
                proposed_duration_min=(
                    planned.planned_duration_min
                ),
                reason=(
                    "Multiple recent sessions were "
                    "classified as too_hard. "
                    "Review recent training response "
                    "before keeping the next workout "
                    "unchanged."
                ),
                evidence=evidence,
                warnings=warnings,
            )

        return AdaptationProposal(
            target_date=planned.planned_date,
            original_workout_title=planned.title,
            original_workout_type=(
                planned.workout_type
            ),
            decision=adaptation_decision,
            proposed_workout_type=(
                recommendation
                .recommended_workout_type
            ),
            proposed_distance_km=(
                recommendation
                .recommended_distance_km
            ),
            proposed_duration_min=(
                recommendation
                .recommended_duration_min
            ),
            reason=recommendation.summary,
            evidence=evidence,
            warnings=warnings,
        )

    def _get_planned_workout(
        self,
        target_date: date,
    ):
        rows = (
            self.plan_source
            .fetch_rows()
        )

        planned_workouts = (
            self.plan_importer
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

    @staticmethod
    def _normalize_date(
        value: str | date,
    ) -> date:
        if isinstance(value, date):
            return value

        return date.fromisoformat(value)