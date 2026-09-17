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
    perceived_effort=7.0,
    comment=None,
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
        perceived_effort=perceived_effort,
        execution_feeling=execution_feeling,
        comment=comment,
        created_at=now,
        updated_at=now,
    )


def make_fast_finish_structure():
    return {
        "summary": {
            "fast_finish": {
                "detected": True,
                "laps": 1,
                "distance_km": 1.0,
                "avg_pace_sec_per_km": 235.0,
                "preceding_easy_distance_km": 16.0,
                "preceding_median_pace_sec_per_km": 330.0,
                "pace_improvement_percent": 28.8,
            }
        }
    }


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
        == {
            "perceived_effort": 7.0,
            "execution_feeling": "too_hard",
            "comment": None,
        }
    )

    assert (
        "Athlete RPE: 7.0/10."
        in result.evidence
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

    assert (
        result.planned_workout_type
        is None
    )

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
            description=(
                "strength 45min + bike easy 20min"
            ),
        ),
    )

    assert result.status == "on_target"

    assert (
        result.planned_duration_min
        == 20.0
    )


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
            description=(
                "strength 45min + bike easy 20min"
            ),
        ),
    )

    assert result.status == "on_target"

    assert (
        result.planned_duration_min
        is None
    )

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
            description=(
                "strength 45min + bike easy 20min"
            ),
        ),
    )

    assert result.status == "on_target"

    assert (
        result.planned_duration_min
        == 20.0
    )

    assert (
        "Executed duration was target: "
        "20.1 vs planned 20.0."
        in result.evidence
    )


def test_fast_finish_is_reported_without_changing_on_target_status():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="easy_run",
            distance_km=17.05,
            duration_min=87.8,
        ),
        planned_workout=make_plan(
            workout_type="long_run",
            distance_km=17.0,
            duration_min=None,
            title="Long",
            description=(
                "17 km easy, cały spokojnie."
            ),
        ),
        execution_structure=(
            make_fast_finish_structure()
        ),
    )

    assert result.status == "on_target"

    assert (
        "Fast finish detected over the final "
        "1.0 km, approximately 28.8% faster "
        "than the preceding pace."
        in result.evidence
    )

    assert (
        "Fast finish changed the structure of a session "
        "that was planned to remain easy throughout."
        in result.warnings
    )


def test_fast_finish_does_not_warn_for_progression_plan():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="easy_run",
            distance_km=17.0,
            duration_min=87.0,
        ),
        planned_workout=make_plan(
            workout_type=(
                "long_run+progression"
            ),
            distance_km=17.0,
            duration_min=None,
            title="Long + progression",
            description=(
                "Finish progressively."
            ),
        ),
        execution_structure=(
            make_fast_finish_structure()
        ),
    )

    assert (
        result.status
        == "on_target"
    )

    assert any(
        "Fast finish detected"
        in item
        for item in result.evidence
    )

    assert all(
        "planned to remain easy throughout"
        not in item
        for item in result.warnings
    )


def test_review_preserves_full_athlete_feedback():
    result = WorkoutExecutionReviewEngine().review(
        session=make_session(
            workout_type="easy_run",
            distance_km=17.0,
            duration_min=88.0,
        ),
        planned_workout=make_plan(
            workout_type="long_run",
            distance_km=17.0,
            duration_min=None,
            title="Long",
            description="17 km easy",
        ),
        feedback=make_feedback(
            execution_feeling="on_target",
            perceived_effort=6.0,
            comment=(
                "Ostatni kilometr pobiegłem mocno."
            ),
        ),
    )

    assert result.status == "on_target"

    assert (
        result.athlete_feedback
        == {
            "perceived_effort": 6.0,
            "execution_feeling": "on_target",
            "comment": (
                "Ostatni kilometr pobiegłem mocno."
            ),
        }
    )

    assert (
        "Athlete RPE: 6.0/10."
        in result.evidence
    )