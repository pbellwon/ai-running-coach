from datetime import datetime

from app.db.models import WorkoutDB
from app.services.executed_workout_type_resolver import (
    ExecutedWorkoutTypeResolver,
)


def make_workout(
    *,
    sport="running",
    declared_workout_type=None,
    avg_hr=135,
    max_hr=150,
    distance_km=10,
    duration_sec=3300,
    pace=330,
    laps_count=1,
):
    return WorkoutDB(
        source_file="test.fit",
        start_time=datetime(
            2026,
            8,
            1,
            8,
            0,
        ),
        sport=sport,
        distance_km=distance_km,
        duration_sec=duration_sec,
        avg_hr=avg_hr,
        max_hr=max_hr,
        avg_pace_sec_per_km=pace,
        records_count=None,
        laps_count=laps_count,
        declared_workout_type=(
            declared_workout_type
        ),
    )


def test_uses_intervals_declared_threshold():
    workout = make_workout(
        declared_workout_type="threshold"
    )

    result = (
        ExecutedWorkoutTypeResolver()
        .resolve(workout)
    )

    assert result["workout_type"] == "threshold"
    assert (
        result["classification_method"]
        == "intervals_declared_type"
    )
    assert result["confidence"] == 0.9


def test_uses_intervals_declared_easy():
    workout = make_workout(
        declared_workout_type="easy_run"
    )

    result = (
        ExecutedWorkoutTypeResolver()
        .resolve(workout)
    )

    assert result["workout_type"] == "easy_run"


def test_strength_uses_sport_mapping():
    workout = make_workout(
        sport="training",
        declared_workout_type=None,
        distance_km=0,
        pace=None,
    )

    result = (
        ExecutedWorkoutTypeResolver()
        .resolve(workout)
    )

    assert result["workout_type"] == "strength"
    assert (
        result["classification_method"]
        == "sport_mapping"
    )


def test_cycling_uses_sport_mapping():
    workout = make_workout(
        sport="cycling",
        declared_workout_type=None,
        distance_km=None,
        pace=None,
    )

    result = (
        ExecutedWorkoutTypeResolver()
        .resolve(workout)
    )

    assert result["workout_type"] == "bike"


def test_running_without_declared_type_uses_fallback():
    workout = make_workout(
        declared_workout_type=None,
        avg_hr=135,
        distance_km=10,
        duration_sec=3300,
        laps_count=1,
    )

    result = (
        ExecutedWorkoutTypeResolver()
        .resolve(workout)
    )

    assert result["workout_type"] == "easy_run"