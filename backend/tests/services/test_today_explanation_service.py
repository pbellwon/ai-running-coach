from app.models.coach_context import (
    CoachContext,
)
from app.models.today_explanation import (
    TodayExplanation,
)
from app.services.today_explanation_service import (
    TodayExplanationService,
)


class FakeCoachContextService:
    def __init__(
        self,
        context,
    ):
        self.context = context
        self.received_target_date = None

    def build(
        self,
        target_date,
    ):
        self.received_target_date = (
            target_date
        )

        return self.context


def make_ready_context():
    return CoachContext(
        schema_version="1.0",
        target_date="2026-09-13",
        goal={
            "goal_type": "race_time",
            "distance_km": 10,
            "target_time_sec": 2310,
            "target_date": "2026-11-11",
        },
        today={
            "target_date": "2026-09-13",
            "status": "ready",
            "message": None,
            "planned_workout": {
                "title": "Threshold",
                "workout_type": "threshold",
            },
            "recovery": {
                "status": "good",
            },
            "recovery_trend": {
                "status": "stable",
            },
            "training_context": {
                "running_km_7d": 45.0,
            },
            "decision": {
                "decision": "do_as_planned",
                "confidence": 0.84,
                "recovery_status": "good",
                "fatigue_signal": "none",
                "planned_workout_type": (
                    "threshold"
                ),
                "planned_session_role": None,
                "reasons": [
                    "Recovery status is good.",
                    "No meaningful fatigue signal detected.",
                ],
                "warnings": [],
            },
            "recommendation": {
                "decision": "do_as_planned",
                "recommendation_type": (
                    "keep_planned_workout"
                ),
                "reasons": [
                    "Recovery status is good.",
                    "Planned quality session can proceed.",
                ],
                "warnings": [],
            },
        },
        goal_progress={
            "status": "on_track",
            "confidence": 0.75,
        },
        athlete_memory=[
            {
                "category": "environment",
                "memory_text": (
                    "Gorzej znoszę treningi "
                    "i zawody w upale."
                ),
            }
        ],
    )


def test_builds_ready_today_explanation():
    context = make_ready_context()

    fake_context_service = (
        FakeCoachContextService(
            context
        )
    )

    service = TodayExplanationService(
        coach_context_service=(
            fake_context_service
        )
    )

    result = service.build(
        target_date="2026-09-13",
    )

    assert isinstance(
        result,
        TodayExplanation,
    )

    assert (
        result.target_date
        == "2026-09-13"
    )

    assert (
        result.status
        == "ready"
    )

    assert (
        result.decision
        == "do_as_planned"
    )

    assert (
        result.recommendation_type
        == "keep_planned_workout"
    )

    assert (
        result.confidence
        == 0.84
    )

    assert (
        result.key_reasons
        == [
            "Recovery status is good.",
            "No meaningful fatigue signal detected.",
            "Planned quality session can proceed.",
        ]
    )

    assert (
        result.warnings
        == []
    )

    assert (
        result.uncertainties
        == []
    )

    assert (
        result.context[
            "goal"
        ][
            "target_time_sec"
        ]
        == 2310
    )


def test_deduplicates_reasons_and_warnings():
    context = make_ready_context()

    context.today[
        "decision"
    ][
        "warnings"
    ] = [
        "Monitor fatigue."
    ]

    context.today[
        "recommendation"
    ][
        "warnings"
    ] = [
        "Monitor fatigue.",
        "Stop if symptoms worsen.",
    ]

    service = TodayExplanationService(
        coach_context_service=(
            FakeCoachContextService(
                context
            )
        )
    )

    result = service.build(
        target_date="2026-09-13",
    )

    assert (
        result.warnings
        == [
            "Monitor fatigue.",
            "Stop if symptoms worsen.",
        ]
    )


def test_marks_low_confidence_as_uncertainty():
    context = make_ready_context()

    context.today[
        "decision"
    ][
        "confidence"
    ] = 0.55

    service = TodayExplanationService(
        coach_context_service=(
            FakeCoachContextService(
                context
            )
        )
    )

    result = service.build(
        target_date="2026-09-13",
    )

    assert (
        result.uncertainties
        == [
            (
                "Decision confidence is below the "
                "preferred explainability threshold."
            )
        ]
    )


def test_marks_missing_context_as_uncertainty():
    context = make_ready_context()

    context.today[
        "recovery"
    ] = None

    context.today[
        "recovery_trend"
    ] = None

    context.today[
        "training_context"
    ] = None

    service = TodayExplanationService(
        coach_context_service=(
            FakeCoachContextService(
                context
            )
        )
    )

    result = service.build(
        target_date="2026-09-13",
    )

    assert (
        result.uncertainties
        == [
            "Recovery data is unavailable.",
            "Recovery trend data is unavailable.",
            "Training context is unavailable.",
        ]
    )


def test_handles_completed_day_without_decision():
    context = make_ready_context()

    context.today[
        "status"
    ] = "completed"

    context.today[
        "message"
    ] = "Completed: 9.28 km"

    context.today[
        "decision"
    ] = None

    context.today[
        "recommendation"
    ] = None

    service = TodayExplanationService(
        coach_context_service=(
            FakeCoachContextService(
                context
            )
        )
    )

    result = service.build(
        target_date="2026-09-13",
    )

    assert (
        result.status
        == "completed"
    )

    assert (
        result.decision
        is None
    )

    assert (
        result.confidence
        is None
    )

    assert (
        result.key_reasons
        == [
            "Completed: 9.28 km"
        ]
    )

    assert (
        result.uncertainties
        == [
            (
                "No current training decision is required "
                "because the planned workout is already completed."
            )
        ]
    )


def test_passes_target_date_to_context_service():
    context = make_ready_context()

    fake_context_service = (
        FakeCoachContextService(
            context
        )
    )

    service = TodayExplanationService(
        coach_context_service=(
            fake_context_service
        )
    )

    service.build(
        target_date="2026-09-13",
    )

    assert (
        fake_context_service
        .received_target_date
        == "2026-09-13"
    )