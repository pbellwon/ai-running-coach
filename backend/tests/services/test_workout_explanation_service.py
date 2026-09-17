from app.models.workout_explanation import (
    WorkoutExplanation,
)
from app.services.workout_explanation_service import (
    WorkoutExplanationService,
)


SESSION_ID = (
    "session:intervals_icu:i186147008"
)


class FakeExecutionReviewService:
    def __init__(
        self,
        items,
    ):
        self.items = items
        self.received_target_date = None
        self.received_limit = None

    def build(
        self,
        target_date=None,
        limit=3,
    ):
        self.received_target_date = (
            target_date
        )

        self.received_limit = (
            limit
        )

        return self.items


def make_review_item():
    return {
        "session_id": SESSION_ID,
        "date": "2026-09-13",
        "start_time": (
            "2026-09-13T09:21:55"
        ),
        "sport_family": "running",
        "workout_type": "easy_run",
        "distance_km": 17.05,
        "duration_min": 87.8,
        "activities_count": 1,
        "source_files": [
            "intervals_icu:i186147008"
        ],
        "planned_workout": {
            "date": "2026-09-13",
            "title": "Long",
            "workout_type": "long_run",
            "planned_distance_km": 17.0,
            "planned_duration_min": None,
            "priority": "normal",
        },
        "review": {
            "status": "on_target",
            "confidence": 0.9,
            "planned_workout_type": (
                "long_run"
            ),
            "executed_workout_type": (
                "easy_run"
            ),
            "planned_distance_km": 17.0,
            "executed_distance_km": 17.05,
            "planned_duration_min": None,
            "executed_duration_min": 87.8,
            "athlete_feedback": {
                "perceived_effort": 6.0,
                "execution_feeling": (
                    "on_target"
                ),
                "comment": (
                    "Spokojnie i pod kontrolą."
                ),
            },
            "evidence": [
                (
                    "Workout intent matched "
                    "the planned session."
                ),
                (
                    "Executed distance was "
                    "within the target range."
                ),
            ],
            "warnings": [],
        },
    }


def test_builds_workout_explanation():
    review_service = (
        FakeExecutionReviewService(
            [
                make_review_item()
            ]
        )
    )

    service = WorkoutExplanationService(
        execution_review_service=(
            review_service
        )
    )

    result = service.build(
        session_id=SESSION_ID,
        target_date="2026-09-13",
    )

    assert isinstance(
        result,
        WorkoutExplanation,
    )

    assert (
        result.session_id
        == SESSION_ID
    )

    assert (
        result.target_date
        == "2026-09-13"
    )

    assert (
        result.status
        == "on_target"
    )

    assert (
        result.confidence
        == 0.9
    )

    assert (
        result.planned_workout[
            "title"
        ]
        == "Long"
    )

    assert (
        result.executed_workout[
            "distance_km"
        ]
        == 17.05
    )

    assert (
        result.athlete_feedback[
            "perceived_effort"
        ]
        == 6.0
    )

    assert (
        result.athlete_feedback[
            "execution_feeling"
        ]
        == "on_target"
    )

    assert (
        result.uncertainties
        == []
    )

    assert (
        review_service
        .received_target_date
        == "2026-09-13"
    )

    assert (
        review_service
        .received_limit
        == 25
    )


def test_marks_missing_feedback_as_uncertainty():
    item = make_review_item()

    item[
        "review"
    ][
        "athlete_feedback"
    ] = None

    service = WorkoutExplanationService(
        execution_review_service=(
            FakeExecutionReviewService(
                [item]
            )
        )
    )

    result = service.build(
        session_id=SESSION_ID,
    )

    assert (
        result.uncertainties
        == [
            (
                "No athlete feedback is available "
                "for this workout."
            )
        ]
    )


def test_marks_low_confidence_and_missing_plan():
    item = make_review_item()

    item["planned_workout"] = None

    item[
        "review"
    ][
        "confidence"
    ] = 0.35

    service = WorkoutExplanationService(
        execution_review_service=(
            FakeExecutionReviewService(
                [item]
            )
        )
    )

    result = service.build(
        session_id=SESSION_ID,
    )

    assert (
        result.uncertainties
        == [
            (
                "Execution-review confidence is below "
                "the preferred explainability threshold."
            ),
            (
                "No planned workout was matched "
                "to this completed session."
            ),
        ]
    )


def test_raises_when_session_is_not_found():
    service = WorkoutExplanationService(
        execution_review_service=(
            FakeExecutionReviewService(
                []
            )
        )
    )

    try:
        service.build(
            session_id=SESSION_ID,
        )

    except LookupError as exc:
        assert (
            str(exc)
            == (
                "Workout session was not found."
            )
        )

    else:
        raise AssertionError(
            "Expected LookupError."
        )


def test_rejects_empty_session_id():
    service = WorkoutExplanationService(
        execution_review_service=(
            FakeExecutionReviewService(
                []
            )
        )
    )

    try:
        service.build(
            session_id="   ",
        )

    except ValueError as exc:
        assert (
            str(exc)
            == (
                "session_id must not be empty."
            )
        )

    else:
        raise AssertionError(
            "Expected ValueError."
        )