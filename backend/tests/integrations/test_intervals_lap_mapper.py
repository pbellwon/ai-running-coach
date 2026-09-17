from app.integrations.intervals_lap_mapper import (
    IntervalsLapMapper,
)


def test_maps_intervals_to_laps():
    mapper = IntervalsLapMapper()

    intervals = [
        {
            "distance": 998.5,
            "elapsed_time": 324,
            "average_heartrate": 138,
            "max_heartrate": 145,
        },
        {
            "distance": 1002.6,
            "elapsed_time": 245,
            "average_heartrate": 159,
            "max_heartrate": 168,
        },
    ]

    laps = mapper.map(
        workout_file=(
            "intervals_icu:i186147008"
        ),
        intervals=intervals,
    )

    assert len(laps) == 2

    assert (
        laps[0].workout_file
        == "intervals_icu:i186147008"
    )

    assert laps[0].lap_number == 1
    assert laps[0].distance_m == 998.5
    assert (
        laps[0].elapsed_time_sec
        == 324.0
    )
    assert laps[0].avg_hr == 138.0
    assert laps[0].max_hr == 145.0

    assert laps[1].lap_number == 2
    assert laps[1].distance_m == 1002.6
    assert (
        laps[1].elapsed_time_sec
        == 245.0
    )
    assert laps[1].avg_hr == 159.0
    assert laps[1].max_hr == 168.0


def test_skips_invalid_intervals():
    mapper = IntervalsLapMapper()

    intervals = [
        {
            "distance": None,
            "elapsed_time": 100,
        },
        {
            "distance": 1000,
            "elapsed_time": 0,
        },
        {
            "distance": 1000,
            "elapsed_time": 300,
        },
    ]

    laps = mapper.map(
        workout_file="intervals_icu:test",
        intervals=intervals,
    )

    assert len(laps) == 1
    assert laps[0].lap_number == 1
    assert laps[0].distance_m == 1000.0


def test_allows_missing_heart_rate():
    mapper = IntervalsLapMapper()

    laps = mapper.map(
        workout_file="intervals_icu:test",
        intervals=[
            {
                "distance": 1000,
                "elapsed_time": 300,
                "average_heartrate": None,
                "max_heartrate": None,
            }
        ],
    )

    assert len(laps) == 1
    assert laps[0].avg_hr is None
    assert laps[0].max_hr is None


def test_rejects_empty_workout_file():
    mapper = IntervalsLapMapper()

    try:
        mapper.map(
            workout_file="",
            intervals=[],
        )

    except ValueError as exc:
        assert (
            str(exc)
            == (
                "workout_file must not be empty."
            )
        )

    else:
        raise AssertionError(
            "Expected ValueError."
        )