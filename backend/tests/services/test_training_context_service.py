from datetime import datetime, timedelta

from app.models.executed_session import ExecutedSession
from app.services.training_context_service import (
    TrainingContextService,
)


def make_session(
    session_id: str,
    start_time: datetime,
    workout_type: str,
    sport_family: str,
    distance_km: float | None,
    duration_min: float,
) -> ExecutedSession:
    return ExecutedSession(
        session_id=session_id,
        start_time=start_time,
        end_time=(
            start_time
            + timedelta(minutes=duration_min)
        ),
        sport_family=sport_family,
        workout_type=workout_type,
        confidence=0.9,
        classification_method="test",
        components=[],
        total_distance_km=distance_km,
        total_duration_min=duration_min,
        warnings=[],
    )


def test_summarizes_seven_day_training_context():
    sessions = [
        make_session(
            session_id="easy",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            sport_family="running",
            distance_km=10,
            duration_min=55,
        ),
        make_session(
            session_id="quality",
            start_time=datetime(
                2026,
                7,
                30,
                17,
                0,
            ),
            workout_type="threshold",
            sport_family="running",
            distance_km=12,
            duration_min=65,
        ),
        make_session(
            session_id="strength",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="strength",
            sport_family="training",
            distance_km=0,
            duration_min=45,
        ),
        make_session(
            session_id="bike",
            start_time=datetime(
                2026,
                7,
                31,
                18,
                0,
            ),
            workout_type="bike",
            sport_family="cycling",
            distance_km=None,
            duration_min=20,
        ),
        make_session(
            session_id="long",
            start_time=datetime(
                2026,
                8,
                1,
                9,
                0,
            ),
            workout_type="long_run",
            sport_family="running",
            distance_km=16,
            duration_min=90,
        ),
    ]

    result = TrainingContextService().summarize(
        target_date="2026-08-01",
        sessions=sessions,
        source_activities_count=5,
    )

    assert result.source_activities_count == 5
    assert result.logical_sessions_count == 5

    assert result.running_sessions == 3
    assert result.easy_sessions == 1
    assert result.quality_sessions == 1
    assert result.long_run_sessions == 1

    assert result.strength_sessions == 1
    assert result.cycling_sessions == 1
    assert result.other_sessions == 0

    assert result.running_distance_km == 38
    assert result.running_duration_min == 210
    assert result.total_training_min == 275


def test_calculates_recent_48_hour_context():
    sessions = [
        make_session(
            session_id="old",
            start_time=datetime(
                2026,
                7,
                29,
                10,
                0,
            ),
            workout_type="easy_run",
            sport_family="running",
            distance_km=8,
            duration_min=45,
        ),
        make_session(
            session_id="strength",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="strength",
            sport_family="training",
            distance_km=0,
            duration_min=45,
        ),
        make_session(
            session_id="quality",
            start_time=datetime(
                2026,
                8,
                1,
                9,
                0,
            ),
            workout_type="threshold",
            sport_family="running",
            distance_km=12,
            duration_min=65,
        ),
    ]

    result = TrainingContextService().summarize(
        target_date="2026-08-01",
        sessions=sessions,
        source_activities_count=3,
    )

    assert result.recent_48h_sessions == 2

    assert (
        result.recent_48h_training_min
        == 110
    )

    assert (
        result.recent_48h_quality_sessions
        == 1
    )

    assert (
        result.recent_48h_strength_sessions
        == 1
    )


def test_builds_last_session_information():
    sessions = [
        make_session(
            session_id="first",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="strength",
            sport_family="training",
            distance_km=0,
            duration_min=45,
        ),
        make_session(
            session_id="last",
            start_time=datetime(
                2026,
                8,
                1,
                9,
                0,
            ),
            workout_type="easy_run",
            sport_family="running",
            distance_km=10,
            duration_min=60,
        ),
    ]

    result = TrainingContextService().summarize(
        target_date="2026-08-01",
        sessions=sessions,
        source_activities_count=2,
    )

    assert result.last_session is not None
    assert result.last_session.session_id == "last"
    assert (
        result.last_session.workout_type
        == "easy_run"
    )
    assert result.last_session.distance_km == 10

    # Session ended at 10:00.
    # Window ends at 00:00 on 2026-08-02.
    assert (
        result.last_session.hours_before_window_end
        == 14
    )


def test_empty_context_is_allowed():
    result = TrainingContextService().summarize(
        target_date="2026-08-01",
        sessions=[],
        source_activities_count=0,
    )

    assert result.logical_sessions_count == 0
    assert result.total_training_min == 0
    assert result.running_distance_km == 0
    assert result.recent_48h_sessions == 0
    assert result.last_session is None