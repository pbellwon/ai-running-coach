from types import SimpleNamespace

from app.analysis.executed_workout_structure_analyzer import (
    ExecutedWorkoutStructureAnalyzer,
)


def make_lap(
    lap_number: int,
    distance_m: float,
    elapsed_time_sec: float,
    avg_hr: float | None = None,
):
    return SimpleNamespace(
        lap_number=lap_number,
        distance_m=distance_m,
        elapsed_time_sec=elapsed_time_sec,
        avg_hr=avg_hr,
    )


def test_detects_fast_finish_after_easy_running():
    analyzer = (
        ExecutedWorkoutStructureAnalyzer()
    )

    easy_laps = [
        make_lap(
            lap_number=index,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        )
        for index in range(
            1,
            17,
        )
    ]

    fast_last_lap = make_lap(
        lap_number=17,
        distance_m=1000,
        elapsed_time_sec=235,
        avg_hr=172,
    )

    laps = (
        easy_laps
        + [
            fast_last_lap
        ]
    )

    result = (
        analyzer._detect_fast_finish(
            laps
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["laps"]
        == 1
    )

    assert (
        result["distance_km"]
        == 1.0
    )

    assert (
        result[
            "preceding_easy_distance_km"
        ]
        == 16.0
    )

    assert (
        result[
            "avg_pace_sec_per_km"
        ]
        == 235.0
    )


def test_does_not_detect_fast_finish_when_last_lap_is_easy():
    analyzer = (
        ExecutedWorkoutStructureAnalyzer()
    )

    laps = [
        make_lap(
            lap_number=index,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        )
        for index in range(
            1,
            18,
        )
    ]

    result = (
        analyzer._detect_fast_finish(
            laps
        )
    )

    assert (
        result["detected"]
        is False
    )


def test_does_not_detect_fast_finish_without_substantial_easy_lead_in():
    analyzer = (
        ExecutedWorkoutStructureAnalyzer()
    )

    laps = [
        make_lap(
            lap_number=1,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        ),
        make_lap(
            lap_number=2,
            distance_m=1000,
            elapsed_time_sec=235,
            avg_hr=172,
        ),
    ]

    result = (
        analyzer._detect_fast_finish(
            laps
        )
    )

    assert (
        result["detected"]
        is False
    )

def test_detects_fast_finish_before_short_trailing_partial_lap():
    analyzer = (
        ExecutedWorkoutStructureAnalyzer()
    )

    laps = [
        make_lap(
            lap_number=index,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        )
        for index in range(
            1,
            17,
        )
    ]

    laps.append(
        make_lap(
            lap_number=17,
            distance_m=1002.6,
            elapsed_time_sec=245,
            avg_hr=159,
        )
    )

    laps.append(
        make_lap(
            lap_number=18,
            distance_m=40,
            elapsed_time_sec=13,
            avg_hr=167,
        )
    )

    result = (
        analyzer._detect_fast_finish(
            laps
        )
    )

    assert (
        result["detected"]
        is True
    )

    assert (
        result["lap_numbers"]
        == [17]
    )

    assert (
        result["distance_km"]
        == 1.0
    )

    assert (
        result[
            "trailing_partial_distance_km"
        ]
        == 0.04
    )