from app.integrations.intervals_activity_mapper import (
    IntervalsActivityMapper,
)


def test_maps_intervals_run_to_workout_db():
    activity = {
        "id": "i168521475",
        "start_date_local": (
            "2026-07-23T18:03:43"
        ),
        "type": "Run",
        "distance": 9237.1,
        "moving_time": 3034,
        "elapsed_time": 3316,
        "average_heartrate": 135,
        "max_heartrate": 153,
        "icu_lap_count": 21,
    }

    workout = (
        IntervalsActivityMapper().map(
            activity
        )
    )

    assert (
        workout.source_file
        == "intervals_icu:i168521475"
    )

    assert (
        workout.start_time.isoformat()
        == "2026-07-23T18:03:43"
    )

    assert workout.sport == "running"
    assert workout.distance_km == 9.237
    assert workout.duration_sec == 3034
    assert workout.avg_hr == 135
    assert workout.max_hr == 153
    assert workout.laps_count == 21

    assert round(
        workout.avg_pace_sec_per_km,
        1,
    ) == 328.5


def test_uses_recording_time_when_moving_time_missing():
    activity = {
        "id": "i1",
        "start_date_local": (
            "2026-07-23T18:03:43"
        ),
        "type": "Run",
        "distance": 5000,
        "moving_time": None,
        "icu_recording_time": 1800,
        "elapsed_time": 1900,
    }

    workout = (
        IntervalsActivityMapper().map(
            activity
        )
    )

    assert workout.duration_sec == 1800


def test_zero_distance_does_not_create_pace():
    activity = {
        "id": "i2",
        "start_date_local": (
            "2026-07-23T18:03:43"
        ),
        "type": "WeightTraining",
        "distance": 0,
        "moving_time": 2700,
    }

    workout = (
        IntervalsActivityMapper().map(
            activity
        )
    )

    assert workout.sport == "training"
    assert workout.avg_pace_sec_per_km is None