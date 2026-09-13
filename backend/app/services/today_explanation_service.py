from __future__ import annotations

from app.models.today_explanation import (
    TodayExplanation,
)
from app.services.coach_context_service import (
    CoachContextService,
)


class TodayExplanationService:
    """
    Builds deterministic explainability data for
    today's PaceMind recommendation.

    The service does not call an LLM.

    It exposes:
    - the decision;
    - recommendation type;
    - confidence;
    - deterministic reasons;
    - warnings;
    - uncertainty signals;
    - full structured coach context.

    A future LLM layer may turn this object into
    natural-language coaching explanation.
    """

    LOW_CONFIDENCE_THRESHOLD = 0.70

    def __init__(
        self,
        coach_context_service=None,
    ):
        self.coach_context_service = (
            coach_context_service
            if coach_context_service
            is not None
            else CoachContextService()
        )

    def build(
        self,
        target_date: str,
    ) -> TodayExplanation:
        coach_context = (
            self.coach_context_service
            .build(
                target_date=target_date
            )
        )

        today = coach_context.today

        status = today.get(
            "status",
            "unknown",
        )

        decision_data = today.get(
            "decision"
        )

        recommendation_data = today.get(
            "recommendation"
        )

        if decision_data is None:
            return self._build_without_decision(
                coach_context=coach_context,
                status=status,
            )

        decision = decision_data.get(
            "decision"
        )

        confidence = decision_data.get(
            "confidence"
        )

        recommendation_type = None

        if recommendation_data is not None:
            recommendation_type = (
                recommendation_data.get(
                    "recommendation_type"
                )
            )

        key_reasons = (
            self._collect_reasons(
                decision_data=decision_data,
                recommendation_data=(
                    recommendation_data
                ),
            )
        )

        warnings = (
            self._collect_warnings(
                decision_data=decision_data,
                recommendation_data=(
                    recommendation_data
                ),
            )
        )

        uncertainties = (
            self._build_uncertainties(
                confidence=confidence,
                today=today,
            )
        )

        return TodayExplanation(
            target_date=(
                coach_context.target_date
            ),
            status=status,
            decision=decision,
            recommendation_type=(
                recommendation_type
            ),
            confidence=confidence,
            key_reasons=key_reasons,
            warnings=warnings,
            uncertainties=uncertainties,
            context={
                "goal": (
                    coach_context.goal
                ),
                "today": (
                    coach_context.today
                ),
                "goal_progress": (
                    coach_context
                    .goal_progress
                ),
                "athlete_memory": (
                    coach_context
                    .athlete_memory
                ),
            },
        )

    def _build_without_decision(
        self,
        coach_context,
        status: str,
    ) -> TodayExplanation:
        today = coach_context.today

        reasons: list[str] = []
        uncertainties: list[str] = []

        message = today.get(
            "message"
        )

        if message:
            reasons.append(
                message
            )

        if status == "completed":
            uncertainties.append(
                "No current training decision is required "
                "because the planned workout is already completed."
            )

        elif status == "no_planned_workout":
            uncertainties.append(
                "No training decision is available because "
                "there is no planned workout for this date."
            )

        else:
            uncertainties.append(
                "No deterministic training decision is "
                "available for this date."
            )

        return TodayExplanation(
            target_date=(
                coach_context.target_date
            ),
            status=status,
            decision=None,
            recommendation_type=None,
            confidence=None,
            key_reasons=reasons,
            warnings=[],
            uncertainties=uncertainties,
            context={
                "goal": (
                    coach_context.goal
                ),
                "today": (
                    coach_context.today
                ),
                "goal_progress": (
                    coach_context
                    .goal_progress
                ),
                "athlete_memory": (
                    coach_context
                    .athlete_memory
                ),
            },
        )

    def _collect_reasons(
        self,
        decision_data: dict,
        recommendation_data: dict | None,
    ) -> list[str]:
        result: list[str] = []

        for reason in decision_data.get(
            "reasons",
            [],
        ):
            if reason not in result:
                result.append(reason)

        if recommendation_data is not None:
            for reason in (
                recommendation_data.get(
                    "reasons",
                    [],
                )
            ):
                if reason not in result:
                    result.append(reason)

        return result

    def _collect_warnings(
        self,
        decision_data: dict,
        recommendation_data: dict | None,
    ) -> list[str]:
        result: list[str] = []

        for warning in decision_data.get(
            "warnings",
            [],
        ):
            if warning not in result:
                result.append(warning)

        if recommendation_data is not None:
            for warning in (
                recommendation_data.get(
                    "warnings",
                    [],
                )
            ):
                if warning not in result:
                    result.append(warning)

        return result

    def _build_uncertainties(
        self,
        confidence: float | None,
        today: dict,
    ) -> list[str]:
        result: list[str] = []

        if confidence is None:
            result.append(
                "Decision confidence is unavailable."
            )

        elif (
            confidence
            < self.LOW_CONFIDENCE_THRESHOLD
        ):
            result.append(
                "Decision confidence is below the "
                "preferred explainability threshold."
            )

        recovery = today.get(
            "recovery"
        )

        if recovery is None:
            result.append(
                "Recovery data is unavailable."
            )

        recovery_trend = today.get(
            "recovery_trend"
        )

        if recovery_trend is None:
            result.append(
                "Recovery trend data is unavailable."
            )

        training_context = today.get(
            "training_context"
        )

        if training_context is None:
            result.append(
                "Training context is unavailable."
            )

        return result