from __future__ import annotations

from app.models.recovery_snapshot import RecoverySnapshot
from app.models.recovery_trend import RecoveryTrend
from app.models.training_context import TrainingContext
from app.models.training_decision import TrainingDecision


class TrainingDecisionEngine:
    """
    Produces a simple daily training decision.

    MVP decisions:
    - do_as_planned
    - reduce
    - easy_only
    - rest

    This engine intentionally uses explicit rules.
    LLM interpretation will be added later.
    """

    QUALITY_TYPES = {
        "threshold",
        "tempo",
        "tempo_run",
        "intervals",
        "vo2max",
        "race",
    }

    EASY_TYPES = {
        "easy_run",
        "recovery_run",
        "easy_run+strides",
        "easy_run+hills",
    }

    def decide(
        self,
        recovery: RecoverySnapshot,
        trend: RecoveryTrend,
        training_context: TrainingContext,
        planned_workout_type: str | None,
        planned_session_role: str | None = None,
    ) -> TrainingDecision:
        reasons: list[str] = []
        warnings: list[str] = []

        is_quality_day = (
            planned_workout_type in self.QUALITY_TYPES
        )

        is_easy_day = (
            planned_workout_type in self.EASY_TYPES
        )

        if recovery.overall_status == "poor":
            reasons.append(
                "Current recovery status is poor."
            )

        if trend.fatigue_signal == "high":
            reasons.append(
                "Recent recovery trend indicates high fatigue."
            )

        if trend.fatigue_signal == "accumulating":
            reasons.append(
                "Fatigue appears to be accumulating."
            )

        if (
            training_context.recent_48h_quality_sessions
            >= 1
        ):
            warnings.append(
                "A quality session was completed "
                "within the last 48 hours."
            )

        if (
            training_context.recent_48h_strength_sessions
            >= 1
        ):
            warnings.append(
                "A strength session was completed "
                "within the last 48 hours."
            )

        decision = self._resolve_decision(
            recovery=recovery,
            trend=trend,
            training_context=training_context,
            is_quality_day=is_quality_day,
            is_easy_day=is_easy_day,
        )

        confidence = self._calculate_confidence(
            recovery=recovery,
            trend=trend,
        )

        if not reasons:
            reasons.append(
                "No strong recovery or fatigue signal "
                "requires a training change."
            )

        return TrainingDecision(
            decision=decision,
            confidence=confidence,
            recovery_status=recovery.overall_status,
            fatigue_signal=trend.fatigue_signal,
            planned_workout_type=planned_workout_type,
            planned_session_role=planned_session_role,
            reasons=reasons,
            warnings=warnings,
        )

    def _resolve_decision(
        self,
        recovery: RecoverySnapshot,
        trend: RecoveryTrend,
        training_context: TrainingContext,
        is_quality_day: bool,
        is_easy_day: bool,
    ) -> str:
        if (
            recovery.overall_status == "poor"
            and trend.fatigue_signal == "high"
        ):
            return "rest"

        if (
            recovery.overall_status == "poor"
            and is_quality_day
        ):
            return "easy_only"

        if (
            trend.fatigue_signal == "high"
            and is_quality_day
        ):
            return "easy_only"

        if (
            trend.fatigue_signal == "accumulating"
            and is_quality_day
        ):
            return "reduce"

        if (
            recovery.overall_status == "caution"
            and is_quality_day
        ):
            return "reduce"

        if (
            training_context.recent_48h_quality_sessions
            >= 1
            and is_quality_day
        ):
            return "reduce"

        if (
            recovery.overall_status == "poor"
            and is_easy_day
        ):
            return "reduce"

        return "do_as_planned"

    def _calculate_confidence(
        self,
        recovery: RecoverySnapshot,
        trend: RecoveryTrend,
    ) -> float:
        score = 1.0

        if (
            recovery.available_metrics_count
            < 3
        ):
            score -= 0.2

        if (
            trend.available_days
            < trend.window_days
        ):
            score -= 0.15

        if (
            recovery.overall_status
            == "insufficient_data"
        ):
            score -= 0.25

        if (
            trend.fatigue_signal
            == "insufficient_data"
        ):
            score -= 0.25

        return round(
            max(
                0.3,
                min(
                    1.0,
                    score,
                ),
            ),
            2,
        )