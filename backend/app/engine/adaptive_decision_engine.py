
from __future__ import annotations

from app.models.adaptation_proposal import AdaptationProposal
from app.models.adaptive_feedback import AdaptiveFeedback
from app.models.planned_workout import PlannedWorkout
from app.models.workout_feedback import WorkoutFeedback


class AdaptiveDecisionEngine:
    """Proposes an adaptation without modifying the training plan."""

    def generate(
        self,
        next_workout: PlannedWorkout,
        execution_assessment: AdaptiveFeedback,
        athlete_feedback: WorkoutFeedback | None = None,
        recent_reviews: list[dict] | None = None,
    ) -> AdaptationProposal:
        evidence = [
            f"Previous workout decision: "
            f"{execution_assessment.decision}.",
            f"Assessment confidence: "
            f"{execution_assessment.confidence:.2f}.",
        ]

        warnings = list(execution_assessment.warnings)

        # Add context from recent executed sessions.
        if recent_reviews:
            evidence.append(
                f"Recent sessions reviewed: {len(recent_reviews)}."
            )

            for session in recent_reviews:
                review = session.get("review") or {}

                evidence.append(
                    f"Session {session.get('date', 'unknown')}: "
                    f"status={review.get('status', 'unknown')}, "
                    f"confidence={review.get('confidence', 'unknown')}."
                )

        # Add subjective athlete feedback.
        if (
            athlete_feedback is not None
            and athlete_feedback.execution_feeling is not None
        ):
            evidence.append(
                f"Athlete execution feeling: "
                f"{athlete_feedback.execution_feeling}."
            )

        if (
            athlete_feedback is not None
            and athlete_feedback.perceived_effort is not None
        ):
            evidence.append(
                f"Athlete RPE: "
                f"{athlete_feedback.perceived_effort:.1f}/10."
            )

        # Insufficient confidence: manual review.
        if (
            execution_assessment.confidence < 0.5
            or execution_assessment.decision == "review_manually"
        ):
            return self._proposal(
                next_workout=next_workout,
                decision="manual_review",
                reason=(
                    "Previous workout assessment does not provide "
                    "sufficient evidence for an automatic adaptation."
                ),
                evidence=evidence,
                warnings=warnings,
            )

        # Previous assessment indicates a potential adaptation.
        if execution_assessment.decision == "adjust_next_workout":
            return self._proposal(
                next_workout=next_workout,
                decision="manual_review",
                reason=(
                    "Previous workout assessment indicates a possible "
                    "need to adjust the next workout. The appropriate "
                    "change requires additional training context."
                ),
                evidence=evidence,
                warnings=warnings,
            )

        # Athlete-reported difficulty requires further review.
        if (
            athlete_feedback is not None
            and athlete_feedback.execution_feeling == "too_hard"
        ):
            return self._proposal(
                next_workout=next_workout,
                decision="manual_review",
                reason=(
                    "Athlete reported that the previous workout was "
                    "too hard. Review recovery and the next workout "
                    "before proposing a load change."
                ),
                evidence=evidence,
                warnings=warnings,
            )
        
        # Repeated difficulty signals in recent sessions.
        recent_sessions = (recent_reviews or [])[:3]

        hard_sessions = [
            session
            for session in recent_sessions
            if (
                (session.get("review") or {}).get("status")
                == "too_hard"
                and (
                    (session.get("review") or {}).get("confidence")
                    or 0
                ) >= 0.5
            )
        ]

        if len(hard_sessions) >= 2:
            evidence.append(
                f"Repeated difficulty: {len(hard_sessions)} "
                f"of {len(recent_sessions)} recent sessions "
                f"were classified as too_hard."
            )

            return self._proposal(
                next_workout=next_workout,
                decision="manual_review",
                reason=(
                    "Multiple recent sessions were classified as "
                    "too_hard. Review the athlete's recovery and "
                    "upcoming training load before changing the plan."
                ),
                evidence=evidence,
                warnings=warnings,
            )

        # No actionable adaptation signal.
        return self._proposal(
            next_workout=next_workout,
            decision="keep_plan",
            reason=(
                "Available information does not indicate a need "
                "to change the next planned workout."
            ),
            evidence=evidence,
            warnings=warnings,
        )

    @staticmethod
    def _proposal(
        next_workout: PlannedWorkout,
        decision: str,
        reason: str,
        evidence: list[str],
        warnings: list[str],
    ) -> AdaptationProposal:
        return AdaptationProposal(
            target_date=next_workout.planned_date,
            original_workout_title=next_workout.title,
            original_workout_type=next_workout.workout_type,
            decision=decision,
            proposed_workout_type=next_workout.workout_type,
            proposed_distance_km=next_workout.planned_distance_km,
            proposed_duration_min=next_workout.planned_duration_min,
            reason=reason,
            evidence=evidence,
            warnings=warnings,
        )