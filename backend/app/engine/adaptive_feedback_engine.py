from app.models.adaptive_feedback import AdaptiveFeedback
from app.models.workout_execution_comparison import WorkoutExecutionComparison


class AdaptiveFeedbackEngine:

    def generate(
        self,
        comparison: WorkoutExecutionComparison,
    ) -> AdaptiveFeedback:

        warnings = list(comparison.warnings)

        if comparison.confidence < 0.5:
            return AdaptiveFeedback(
                decision="review_manually",
                risk_level="unknown",
                reason="Execution classification confidence is too low for automatic coaching decision.",
                next_action="Review workout manually before changing the plan.",
                confidence=comparison.confidence,
                warnings=warnings,
            )

        if comparison.execution_quality == "good":
            return AdaptiveFeedback(
                decision="continue_plan",
                risk_level="low",
                reason="Workout matched the plan well.",
                next_action="Continue with the planned training schedule.",
                confidence=comparison.confidence,
                warnings=warnings,
            )

        if comparison.execution_quality == "acceptable":
            return AdaptiveFeedback(
                decision="continue_with_note",
                risk_level="low_to_moderate",
                reason="Workout mostly matched the plan, but there were minor differences.",
                next_action="Continue the plan, but monitor the next workout response.",
                confidence=comparison.confidence,
                warnings=warnings,
            )

        if not comparison.intent_match:
            return AdaptiveFeedback(
                decision="review_manually",
                risk_level="moderate",
                reason="Executed workout intent did not match the planned workout intent.",
                next_action="Do not automatically adjust fitness assumptions from this workout.",
                confidence=comparison.confidence,
                warnings=warnings,
            )

        if comparison.distance_match == "major_difference":
            return AdaptiveFeedback(
                decision="adjust_next_workout",
                risk_level="moderate",
                reason="Executed distance differed significantly from the planned distance.",
                next_action="Review next planned workout load before continuing.",
                confidence=comparison.confidence,
                warnings=warnings,
            )

        if comparison.structure_match == "mismatch":
            return AdaptiveFeedback(
                decision="review_manually",
                risk_level="moderate",
                reason="Executed workout structure did not match the planned structure.",
                next_action="Review workout execution before adapting the plan.",
                confidence=comparison.confidence,
                warnings=warnings,
            )

        return AdaptiveFeedback(
            decision="review_manually",
            risk_level="unknown",
            reason="Workout comparison did not produce a clear coaching decision.",
            next_action="Review workout manually.",
            confidence=comparison.confidence,
            warnings=warnings,
        )