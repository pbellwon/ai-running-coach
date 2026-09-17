from __future__ import annotations

from datetime import date

from app.models.workout_explanation import (
    WorkoutExplanation,
)
from app.services.recent_execution_review_service import (
    RecentExecutionReviewService,
)


class WorkoutExplanationService:
    """
    Builds deterministic explainability data for one
    completed workout.

    This service does not call an LLM.

    It reuses RecentExecutionReviewService so that plan matching,
    athlete feedback, execution structure and execution-review
    logic remain centralized.
    """

    LOOKUP_LIMIT = 25
    LOW_CONFIDENCE_THRESHOLD = 0.70

    def __init__(
        self,
        execution_review_service=None,
    ):
        self.execution_review_service = (
            execution_review_service
            if execution_review_service is not None
            else RecentExecutionReviewService()
        )

    def build(
        self,
        session_id: str,
        target_date: (
            date
            | str
            | None
        ) = None,
    ) -> WorkoutExplanation:
        normalized_session_id = (
            session_id.strip()
        )

        if not normalized_session_id:
            raise ValueError(
                "session_id must not be empty."
            )

        reviews = (
            self.execution_review_service
            .build(
                target_date=target_date,
                limit=self.LOOKUP_LIMIT,
            )
        )

        item = next(
            (
                review
                for review in reviews
                if review.get(
                    "session_id"
                ) == normalized_session_id
            ),
            None,
        )

        if item is None:
            raise LookupError(
                "Workout session was not found."
            )

        review = (
            item.get("review")
            or {}
        )

        execution_structure = (
            item.get(
                "execution_structure"
            )
        )

        status = (
            review.get("status")
            or "insufficient_evidence"
        )

        confidence = (
            review.get("confidence")
        )

        if confidence is None:
            confidence = 0.0

        athlete_feedback = (
            review.get(
                "athlete_feedback"
            )
        )

        key_evidence = list(
            review.get(
                "evidence"
            )
            or []
        )

        warnings = list(
            review.get(
                "warnings"
            )
            or []
        )

        uncertainties = (
            self._build_uncertainties(
                confidence=confidence,
                planned_workout=(
                    item.get(
                        "planned_workout"
                    )
                ),
                athlete_feedback=(
                    athlete_feedback
                ),
                key_evidence=(
                    key_evidence
                ),
            )
        )

        executed_workout = {
            "date": item.get(
                "date"
            ),
            "start_time": item.get(
                "start_time"
            ),
            "sport_family": item.get(
                "sport_family"
            ),
            "workout_type": item.get(
                "workout_type"
            ),
            "distance_km": item.get(
                "distance_km"
            ),
            "duration_min": item.get(
                "duration_min"
            ),
            "activities_count": item.get(
                "activities_count"
            ),
        }

        return WorkoutExplanation(
            session_id=(
                normalized_session_id
            ),
            target_date=(
                item.get("date")
                or ""
            ),
            status=status,
            confidence=float(
                confidence
            ),
            planned_workout=(
                item.get(
                    "planned_workout"
                )
            ),
            executed_workout=(
                executed_workout
            ),
            athlete_feedback=(
                athlete_feedback
            ),
            key_evidence=(
                key_evidence
            ),
            warnings=warnings,
            uncertainties=(
                uncertainties
            ),
            context={
                "review": review,
            },
            execution_structure=(
                execution_structure
            ),
        )

    def _build_uncertainties(
        self,
        *,
        confidence: float,
        planned_workout: dict | None,
        athlete_feedback,
        key_evidence: list[str],
    ) -> list[str]:
        result: list[str] = []

        if (
            confidence
            < self.LOW_CONFIDENCE_THRESHOLD
        ):
            result.append(
                "Execution-review confidence is below "
                "the preferred explainability threshold."
            )

        if planned_workout is None:
            result.append(
                "No planned workout was matched "
                "to this completed session."
            )

        if athlete_feedback is None:
            result.append(
                "No athlete feedback is available "
                "for this workout."
            )

        if not key_evidence:
            result.append(
                "No execution-review evidence "
                "is available."
            )

        return result