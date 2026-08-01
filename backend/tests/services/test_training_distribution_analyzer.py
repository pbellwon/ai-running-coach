from datetime import datetime, timedelta

from app.models.executed_session import ExecutedSession
from app.services.training_distribution_analyzer import (
    TrainingDistributionAnalyzer,
)


def make_session(
    session_id: str,
    workout_type: str,
    distance_km: float | None,
    duration_min: float | None,
    sport_family: str,
) -> ExecutedSession:
    start_time = datetime(2025, 6, 2, 8, 0)

    end_time = start_time + timedelta(
        minutes=duration_min or 0
    )

    return ExecutedSession(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        sport_family=sport_family,
        workout_type=workout_type,
        confidence=0.9,
        classification_method="test",
        components=[],
        total_distance_km=distance_km,
        total_duration_min=duration_min,
        warnings=[],
    )


def test_analyzes_training_distribution():
    sessions = [
        make_session(
            session_id="easy-1",
            workout_type="easy_run",
            distance_km=8,
            duration_min=48,
            sport_family="running",
        ),
        make_session(
            session_id="easy-2",
            workout_type="easy_run",
            distance_km=7,
            duration_min=44,
            sport_family="running",
        ),
        make_session(
            session_id="quality-1",
            workout_type="threshold",
            distance_km=12,
            duration_min=65,
            sport_family="running",
        ),
        make_session(
            session_id="long-1",
            workout_type="long_run",
            distance_km=16,
            duration_min=90,
            sport_family="running",
        ),
        make_session(
            session_id="strength-1",
            workout_type="strength",
            distance_km=0,
            duration_min=45,
            sport_family="training",
        ),
        make_session(
            session_id="bike-1",
            workout_type="bike",
            distance_km=25,
            duration_min=60,
            sport_family="cycling",
        ),
    ]

    result = TrainingDistributionAnalyzer().analyze(
        sessions
    )

    assert result["session_counts"] == {
        "total": 6,
        "running": 4,
        "easy": 2,
        "quality": 1,
        "long_run": 1,
        "strength": 1,
        "cross_training": 1,
        "mobility": 0,
        "unknown": 0,
    }

    assert result["distance"]["running_total_km"] == 43
    assert result["distance"]["easy_session_km"] == 15
    assert result["distance"]["quality_session_km"] == 12
    assert result["distance"]["quality_component_km"] == 12
    assert result["distance"]["long_run_km"] == 16

    assert (
        result["distance"]["long_run_share_percent"]
        == 37.2
    )

    assert result["duration"]["running_min"] == 247
    assert result["duration"]["strength_min"] == 45
    assert (
        result["duration"]["cross_training_min"]
        == 60
    )
    assert (
        result["duration"]["total_training_min"]
        == 352
    )

    assert (
        result["ratios"][
            "easy_to_quality_session_ratio"
        ]
        == 2
    )

    assert (
        result["ratios"][
            "quality_session_share_percent"
        ]
        == 25
    )


def test_returns_none_when_no_quality_sessions():
    sessions = [
        make_session(
            session_id="easy-1",
            workout_type="easy_run",
            distance_km=8,
            duration_min=48,
            sport_family="running",
        )
    ]

    result = TrainingDistributionAnalyzer().analyze(
        sessions
    )

    assert (
        result["ratios"][
            "easy_to_quality_session_ratio"
        ]
        is None
    )

    assert (
        result["ratios"][
            "quality_session_share_percent"
        ]
        == 0
    )


def test_handles_empty_session_list():
    result = TrainingDistributionAnalyzer().analyze([])

    assert result["session_counts"]["total"] == 0
    assert result["distance"]["running_total_km"] == 0
    assert result["duration"]["total_training_min"] == 0

    assert (
        result["distance"]["long_run_share_percent"]
        is None
    )

    assert (
        result["duration"]["running_share_percent"]
        is None
    )