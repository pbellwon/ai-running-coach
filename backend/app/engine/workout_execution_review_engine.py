from __future__ import annotations

from typing import Any

from app.models.executed_session import (
    ExecutedSession,
)
from app.models.workout_execution_review import (
    WorkoutExecutionReview,
)
from app.models.workout_feedback import (
    WorkoutFeedback,
)


class WorkoutExecutionReviewEngine:
    """
    Deterministic review of a completed logical session.

    Rules for composite strength + cross-training plans:
    - planned_duration_min belongs to the cross-training component;
    - strength duration is not evaluated against planned_duration_min.

    Execution structure may add evidence and warnings without
    automatically changing the overall execution status.
    """

    TOO_LOW_RATIO = 0.85
    TOO_HIGH_RATIO = 1.15

    COMPATIBLE_TYPES = {
        ("easy_run", "easy_run+strides"),
        ("tempo_run", "threshold"),
        ("threshold", "tempo_run"),
        ("long_run", "easy_run"),
        ("long_run", "easy_run+strides"),
        ("long_run+progression", "easy_run"),
        ("long_run+progression", "tempo_run"),
    }

    CROSS_TRAIN_TYPES = {
        "bike",
        "cycling",
        "elliptical",
        "cross_training",
        "cross_train",
    }

    def review(
        self,
        session: ExecutedSession,
        planned_workout: Any | None,
        feedback: WorkoutFeedback | None = None,
        execution_structure: dict | None = None,
    ) -> WorkoutExecutionReview:
        evidence: list[str] = []
        warnings: list[str] = list(
            session.warnings
        )

        planned_type = (
            planned_workout.workout_type
            if planned_workout is not None
            else None
        )

        planned_distance_km = (
            planned_workout.planned_distance_km
            if planned_workout is not None
            else None
        )

        athlete_feedback = (
            self._serialize_feedback(
                feedback
            )
        )

        execution_feeling = (
            feedback.execution_feeling
            if feedback is not None
            else None
        )

        if planned_workout is None:
            self._apply_execution_structure(
                execution_structure=execution_structure,
                planned_workout=None,
                evidence=evidence,
                warnings=warnings,
            )

            if execution_feeling is not None:
                evidence.append(
                    f"Athlete feedback: "
                    f"{execution_feeling}."
                )

            if (
                feedback is not None
                and feedback.perceived_effort
                is not None
            ):
                evidence.append(
                    f"Athlete RPE: "
                    f"{feedback.perceived_effort:.1f}/10."
                )

            return WorkoutExecutionReview(
                session_id=session.session_id,
                planned_workout_type=None,
                executed_workout_type=session.workout_type,
                status="insufficient_evidence",
                confidence=0.35,
                planned_distance_km=None,
                executed_distance_km=(
                    session.total_distance_km
                ),
                planned_duration_min=None,
                executed_duration_min=(
                    session.total_duration_min
                ),
                athlete_feedback=(
                    athlete_feedback
                ),
                evidence=[
                    (
                        "No planned workout matched "
                        "this session."
                    ),
                    *evidence,
                ],
                warnings=warnings,
            )

        planned_duration_min = (
            self._effective_planned_duration_min(
                planned_workout=planned_workout,
                executed_type=session.workout_type,
            )
        )

        intent_match = self._intent_match(
            planned_workout=planned_workout,
            executed_type=session.workout_type,
        )

        if intent_match:
            evidence.append(
                "Executed workout intent matched the plan."
            )
        else:
            evidence.append(
                "Executed workout intent differed from the plan."
            )

        distance_direction = self._volume_direction(
            planned=planned_distance_km,
            executed=session.total_distance_km,
        )

        duration_direction = self._volume_direction(
            planned=planned_duration_min,
            executed=session.total_duration_min,
        )

        if distance_direction is not None:
            evidence.append(
                self._volume_evidence(
                    metric="distance",
                    direction=distance_direction,
                    planned=planned_distance_km,
                    executed=session.total_distance_km,
                )
            )

        if duration_direction is not None:
            evidence.append(
                self._volume_evidence(
                    metric="duration",
                    direction=duration_direction,
                    planned=planned_duration_min,
                    executed=session.total_duration_min,
                )
            )

        objective_status = self._objective_status(
            intent_match=intent_match,
            distance_direction=distance_direction,
            duration_direction=duration_direction,
        )

        status = objective_status

        confidence = self._base_confidence(
            session=session,
            planned_distance_km=planned_distance_km,
            planned_duration_min=planned_duration_min,
        )

        self._apply_execution_structure(
            execution_structure=execution_structure,
            planned_workout=planned_workout,
            evidence=evidence,
            warnings=warnings,
        )

        if execution_feeling is not None:
            evidence.append(
                f"Athlete feedback: "
                f"{execution_feeling}."
            )

            status = self._combine_with_feedback(
                objective_status=objective_status,
                athlete_feedback=execution_feeling,
            )

            confidence = min(
                1.0,
                confidence + 0.1,
            )

        if (
            feedback is not None
            and feedback.perceived_effort
            is not None
        ):
            evidence.append(
                f"Athlete RPE: "
                f"{feedback.perceived_effort:.1f}/10."
            )

        return WorkoutExecutionReview(
            session_id=session.session_id,
            planned_workout_type=planned_type,
            executed_workout_type=session.workout_type,
            status=status,
            confidence=round(
                confidence,
                2,
            ),
            planned_distance_km=planned_distance_km,
            executed_distance_km=(
                session.total_distance_km
            ),
            planned_duration_min=planned_duration_min,
            executed_duration_min=(
                session.total_duration_min
            ),
            athlete_feedback=athlete_feedback,
            evidence=evidence,
            warnings=warnings,
        )

    def _serialize_feedback(
        self,
        feedback: WorkoutFeedback | None,
    ) -> dict | None:
        if feedback is None:
            return None

        return {
            "perceived_effort": (
                feedback.perceived_effort
            ),
            "execution_feeling": (
                feedback.execution_feeling
            ),
            "comment": (
                feedback.comment
            ),
        }

    def _apply_execution_structure(
        self,
        *,
        execution_structure: dict | None,
        planned_workout: Any | None,
        evidence: list[str],
        warnings: list[str],
    ) -> None:
        if not execution_structure:
            return

        summary = (
            execution_structure.get(
                "summary"
            )
            or {}
        )

        fast_finish = (
            summary.get(
                "fast_finish"
            )
            or {}
        )

        if not fast_finish.get(
            "detected"
        ):
            return

        distance_km = (
            fast_finish.get(
                "distance_km"
            )
        )

        pace_improvement = (
            fast_finish.get(
                "pace_improvement_percent"
            )
        )

        evidence_text = (
            "Fast finish detected"
        )

        if distance_km is not None:
            evidence_text += (
                f" over the final "
                f"{distance_km:.1f} km"
            )

        if pace_improvement is not None:
            evidence_text += (
                f", approximately "
                f"{pace_improvement:.1f}% faster "
                f"than the preceding pace"
            )

        evidence_text += "."

        evidence.append(
            evidence_text
        )

        if (
            planned_workout is not None
            and self._plan_expected_easy_throughout(
                planned_workout
            )
        ):
            warnings.append(
                "Fast finish changed the structure of a session "
                "that was planned to remain easy throughout."
            )

    def _plan_expected_easy_throughout(
        self,
        planned_workout: Any,
    ) -> bool:
        planned_type = (
            planned_workout.workout_type
        )

        if planned_type not in {
            "easy_run",
            "long_run",
        }:
            return False

        title = (
            getattr(
                planned_workout,
                "title",
                "",
            )
            or ""
        )

        description = (
            getattr(
                planned_workout,
                "description",
                "",
            )
            or ""
        )

        text = (
            f"{title} {description}"
            .strip()
            .lower()
        )

        easy_markers = {
            "easy",
            "spokoj",
        }

        return any(
            marker in text
            for marker in easy_markers
        )

    def _intent_match(
        self,
        planned_workout: Any,
        executed_type: str,
    ) -> bool:
        planned_type = (
            planned_workout.workout_type
        )

        if planned_type == executed_type:
            return True

        if (
            planned_type,
            executed_type,
        ) in self.COMPATIBLE_TYPES:
            return True

        if (
            executed_type
            in self.CROSS_TRAIN_TYPES
            and self._plan_mentions_cross_training(
                planned_workout
            )
        ):
            return True

        return False

    def _effective_planned_duration_min(
        self,
        planned_workout: Any,
        executed_type: str,
    ) -> float | None:
        is_composite_strength_cross = (
            planned_workout.workout_type
            == "strength"
            and self._plan_mentions_cross_training(
                planned_workout
            )
        )

        if is_composite_strength_cross:
            if executed_type == "strength":
                return None

            if (
                executed_type
                in self.CROSS_TRAIN_TYPES
            ):
                return (
                    planned_workout
                    .planned_duration_min
                )

        return (
            planned_workout
            .planned_duration_min
        )

    def _plan_mentions_cross_training(
        self,
        planned_workout: Any,
    ) -> bool:
        title = (
            getattr(
                planned_workout,
                "title",
                "",
            )
            or ""
        )

        description = (
            getattr(
                planned_workout,
                "description",
                "",
            )
            or ""
        )

        text = (
            f"{title} {description}"
            .strip()
            .lower()
        )

        markers = {
            "cross train",
            "cross-training",
            "cross training",
            "bike",
            "cycling",
            "rower",
            "elliptical",
        }

        return any(
            marker in text
            for marker in markers
        )

    def _volume_direction(
        self,
        planned: float | None,
        executed: float | None,
    ) -> str | None:
        if (
            planned is None
            or executed is None
            or planned <= 0
        ):
            return None

        ratio = (
            executed
            / planned
        )

        if ratio < self.TOO_LOW_RATIO:
            return "low"

        if ratio > self.TOO_HIGH_RATIO:
            return "high"

        return "target"

    def _objective_status(
        self,
        intent_match: bool,
        distance_direction: str | None,
        duration_direction: str | None,
    ) -> str:
        directions = {
            direction
            for direction in (
                distance_direction,
                duration_direction,
            )
            if direction is not None
        }

        if "high" in directions:
            return "too_hard"

        if "low" in directions:
            return "too_easy"

        if intent_match:
            return "on_target"

        return "insufficient_evidence"

    def _combine_with_feedback(
        self,
        objective_status: str,
        athlete_feedback: str,
    ) -> str:
        if athlete_feedback in {
            "too_easy",
            "too_hard",
        }:
            return athlete_feedback

        if (
            athlete_feedback
            == "on_target"
        ):
            if objective_status in {
                "on_target",
                "insufficient_evidence",
            }:
                return "on_target"

        return objective_status

    def _base_confidence(
        self,
        session: ExecutedSession,
        planned_distance_km: float | None,
        planned_duration_min: float | None,
    ) -> float:
        confidence = max(
            0.5,
            session.confidence,
        )

        has_volume_target = (
            planned_distance_km
            is not None
            or planned_duration_min
            is not None
        )

        if has_volume_target:
            confidence += 0.05

        return min(
            confidence,
            0.9,
        )

    def _volume_evidence(
        self,
        metric: str,
        direction: str,
        planned: float,
        executed: float,
    ) -> str:
        return (
            f"Executed {metric} was {direction}: "
            f"{executed:.1f} vs planned {planned:.1f}."
        )