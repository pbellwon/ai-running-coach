from __future__ import annotations

from app.models.today_recommendation import TodayRecommendation
from app.models.training_decision import TrainingDecision


class TodayRecommendationService:
    """
    Converts a TrainingDecision into a concrete recommendation
    for the planned workout.

    MVP scope:
    - keep as planned
    - reduce volume
    - replace with easy running
    - rest
    """

    REDUCTION_FACTOR = 0.70

    def build(
        self,
        decision: TrainingDecision,
        planned_title: str,
        planned_workout_type: str | None,
        planned_distance_km: float | None,
        planned_duration_min: int | None,
    ) -> TodayRecommendation:

        if decision.decision == "do_as_planned":
            return self._as_planned(
                decision=decision,
                planned_title=planned_title,
                planned_workout_type=planned_workout_type,
                planned_distance_km=planned_distance_km,
                planned_duration_min=planned_duration_min,
            )

        if decision.decision == "reduce":
            return self._reduced(
                decision=decision,
                planned_title=planned_title,
                planned_workout_type=planned_workout_type,
                planned_distance_km=planned_distance_km,
                planned_duration_min=planned_duration_min,
            )

        if decision.decision == "easy_only":
            return self._easy_replacement(
                decision=decision,
                planned_title=planned_title,
                planned_distance_km=planned_distance_km,
                planned_duration_min=planned_duration_min,
            )

        if decision.decision == "rest":
            return self._rest(
                decision=decision,
                planned_title=planned_title,
                planned_workout_type=planned_workout_type,
                planned_distance_km=planned_distance_km,
                planned_duration_min=planned_duration_min,
            )

        raise ValueError(
            f"Unsupported training decision: {decision.decision}"
        )

    def _as_planned(
        self,
        decision: TrainingDecision,
        planned_title: str,
        planned_workout_type: str | None,
        planned_distance_km: float | None,
        planned_duration_min: int | None,
    ) -> TodayRecommendation:

        return TodayRecommendation(
            decision=decision.decision,
            recommendation_type="as_planned",
            original_workout_type=planned_workout_type,
            recommended_workout_type=planned_workout_type,
            original_distance_km=planned_distance_km,
            recommended_distance_km=planned_distance_km,
            original_duration_min=planned_duration_min,
            recommended_duration_min=planned_duration_min,
            title=planned_title,
            summary="Complete the planned workout as scheduled.",
            reasons=decision.reasons,
            warnings=decision.warnings,
        )

    def _reduced(
        self,
        decision: TrainingDecision,
        planned_title: str,
        planned_workout_type: str | None,
        planned_distance_km: float | None,
        planned_duration_min: int | None,
    ) -> TodayRecommendation:

        recommended_distance_km = None

        if planned_distance_km is not None:
            recommended_distance_km = round(
                planned_distance_km * self.REDUCTION_FACTOR,
                1,
            )

        recommended_duration_min = None

        if planned_duration_min is not None:
            recommended_duration_min = round(
                planned_duration_min * self.REDUCTION_FACTOR
            )

        return TodayRecommendation(
            decision=decision.decision,
            recommendation_type="reduced",
            original_workout_type=planned_workout_type,
            recommended_workout_type=planned_workout_type,
            original_distance_km=planned_distance_km,
            recommended_distance_km=recommended_distance_km,
            original_duration_min=planned_duration_min,
            recommended_duration_min=recommended_duration_min,
            title=f"Reduced: {planned_title}",
            summary=(
                "Keep the planned workout type, "
                "but reduce total training volume."
            ),
            reasons=decision.reasons,
            warnings=decision.warnings,
        )

    def _easy_replacement(
        self,
        decision: TrainingDecision,
        planned_title: str,
        planned_distance_km: float | None,
        planned_duration_min: int | None,
    ) -> TodayRecommendation:

        recommended_distance_km = None

        if planned_distance_km is not None:
            recommended_distance_km = round(
                planned_distance_km * self.REDUCTION_FACTOR,
                1,
            )

        recommended_duration_min = None

        if planned_duration_min is not None:
            recommended_duration_min = round(
                planned_duration_min * self.REDUCTION_FACTOR
            )

        return TodayRecommendation(
            decision=decision.decision,
            recommendation_type="easy_replacement",
            original_workout_type=decision.planned_workout_type,
            recommended_workout_type="easy_run",
            original_distance_km=planned_distance_km,
            recommended_distance_km=recommended_distance_km,
            original_duration_min=planned_duration_min,
            recommended_duration_min=recommended_duration_min,
            title="Easy run instead of planned quality",
            summary=(
                "Replace the planned workout with an easy run "
                "and keep the session controlled."
            ),
            reasons=decision.reasons,
            warnings=decision.warnings,
        )

    def _rest(
        self,
        decision: TrainingDecision,
        planned_title: str,
        planned_workout_type: str | None,
        planned_distance_km: float | None,
        planned_duration_min: int | None,
    ) -> TodayRecommendation:

        return TodayRecommendation(
            decision=decision.decision,
            recommendation_type="rest",
            original_workout_type=planned_workout_type,
            recommended_workout_type=None,
            original_distance_km=planned_distance_km,
            recommended_distance_km=0.0,
            original_duration_min=planned_duration_min,
            recommended_duration_min=0,
            title="Rest day",
            summary=(
                "Skip the planned workout today and prioritise recovery."
            ),
            reasons=decision.reasons,
            warnings=decision.warnings,
        )