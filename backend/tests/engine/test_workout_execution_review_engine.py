from datetime import datetime, timedelta
from types import SimpleNamespace

from app.engine.workout_execution_review_engine import (
    WorkoutExecutionReviewEngine,
)
from app.models.executed_session import (
    ExecutedSession,
    ExecutedSessionComponent,
)
from app.models.workout_feedback import (
    WorkoutFeedback,
)


def make_session(
    workout_type="threshold",
    distance_km=10.0,
    duration_min=50.0,
    confidence=0.8,
):
    start = datetime(
        2026,
        9,
        10,
        17,
        0,
    )

    component = ExecutedSessionComponent(
        workout=SimpleNamespace(),
        workout_file="test.fit",
        start_time=start,
        end_time=start + timedelta(
            minutes=duration_min
        ),
        sport="running",
        distance_km=distance_km,
        duration_min=duration_min,
        workout_type=workout_type,
        confidence=confidence,
        classification_method="test",
        warnings=[],
        role="main",
    )

    return ExecutedSession(
        session_id="session:test.fit",
        start_time=start,
        end_time=component.end_time,
        sport_family="running",
        workout_type=workout_type,
        confidence=confidence,
        classification_method="test",
        components=[component],
        total_distance_km=distance_km,
        total_duration_min=duration_min,
        warnings=[],
    )


def make_plan(
    workout_type="threshold",
    distance_km=10.0,
    duration_min=50.0,
    title="Threshold",
    description="Threshold session",
):
    return SimpleNamespace(
        workout_type=workout_type,
        planned_distance_km=distance_km,
        planned_duration_min=duration_min,
        title=title,
        description=description,
    )


def make_feedback(
    execution_feeling,
):
    now = datetime(
        2026,
        9,
        10,
        19,
        0,
    )

    return WorkoutFeedback(
        session_id="session:test.fit",
        perceived_effort=7.0,
        execution_feeling=execution_feeling,
        comment=None,
        created_at=now,
        updated_at=now,
    )


def test_review_returns_on_target_for_matching_session():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(),
        planned_workout=make_plan(),
    )

    assert result.status == "on_target"
    assert (
        result.planned_workout_type
        == "threshold"
    )
    assert (
        result.executed_workout_type
        == "threshold"
    )
    assert result.confidence > 0.5


def test_review_returns_too_hard_when_volume_is_too_high():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            distance_km=12.0,
            duration_min=60.0,
        ),
        planned_workout=make_plan(
            distance_km=10.0,
            duration_min=50.0,
        ),
    )

    assert result.status == "too_hard"


def test_review_returns_too_easy_when_volume_is_too_low():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            distance_km=8.0,
            duration_min=40.0,
        ),
        planned_workout=make_plan(
            distance_km=10.0,
            duration_min=50.0,
        ),
    )

    assert result.status == "too_easy"


def test_review_uses_athlete_feedback_when_session_felt_too_hard():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(),
        planned_workout=make_plan(),
        feedback=make_feedback(
            "too_hard"
        ),
    )

    assert result.status == "too_hard"
    assert (
        result.athlete_feedback
        == "too_hard"
    )
    assert result.confidence == 0.95


def test_review_returns_insufficient_evidence_without_plan():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(),
        planned_workout=None,
    )

    assert (
        result.status
        == "insufficient_evidence"
    )
    assert result.planned_workout_type is None
    assert result.confidence == 0.35


def test_long_run_plan_accepts_easy_run_execution():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="easy_run",
            distance_km=18.02,
            duration_min=98.4,
        ),
        planned_workout=make_plan(
            workout_type="long_run",
            distance_km=18.0,
            duration_min=None,
            title="easy long",
            description="18 km easy long run",
        ),
    )

    assert result.status == "on_target"
    assert (
        result.planned_workout_type
        == "long_run"
    )
    assert (
        result.executed_workout_type
        == "easy_run"
    )


def test_cross_training_plan_accepts_bike_execution():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="bike",
            distance_km=None,
            duration_min=20.3,
        ),
        planned_workout=make_plan(
            workout_type="strength",
            distance_km=None,
            duration_min=20.0,
            title="Strength + cross train",
            description="strength 45min + bike easy 20min",
        ),
    )

    assert result.status == "on_target"
    assert result.planned_duration_min == 20.0


def test_composite_strength_does_not_use_cross_training_duration():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="strength",
            distance_km=None,
            duration_min=31.5,
        ),
        planned_workout=make_plan(
            workout_type="strength",
            distance_km=None,
            duration_min=20.0,
            title="Strength + cross train",
            description="strength 45min + bike easy 20min",
        ),
    )

    assert result.status == "on_target"
    assert result.planned_duration_min is None
    assert (
        "Executed workout intent matched the plan."
        in result.evidence
    )
    assert all(
        "duration" not in item.lower()
        for item in result.evidence
    )


def test_composite_plan_uses_duration_for_bike():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="bike",
            distance_km=None,
            duration_min=20.1,
        ),
        planned_workout=make_plan(
            workout_type="strength",
            distance_km=None,
            duration_min=20.0,
            title="Strength + cross train",
            description="strength 45min + bike easy 20min",
        ),
    )

    assert result.status == "on_target"
    assert result.planned_duration_min == 20.0
    assert (
        "Executed duration was target: "
        "20.1 vs planned 20.0."
        in result.evidence
    )