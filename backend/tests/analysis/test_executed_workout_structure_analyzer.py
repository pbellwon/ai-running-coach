
from types import SimpleNamespace

from app.analysis.executed_workout_structure_analyzer import (
    ExecutedWorkoutStructureAnalyzer,
)


def make_lap(
    lap_number: int,
    distance_m: float,
    elapsed_time_sec: float,
    avg_hr: float | None = None,
    moving_time_sec: float | None = None,
):
    return SimpleNamespace(
        lap_number=lap_number,
        distance_m=distance_m,
        elapsed_time_sec=elapsed_time_sec,
        moving_time_sec=moving_time_sec,
        avg_hr=avg_hr,
    )


def make_three_by_ten_threshold_laps():
    """
    Real Intervals.icu lap pattern from 2026-09-16.

    Autolaps divide each ten-minute threshold repetition
    into several measurement fragments.

    One-second technical splits should not become
    separate workout segments.
    """

    return [
        # Warm-up
        make_lap(
            lap_number=1,
            distance_m=1000.5,
            elapsed_time_sec=325,
            avg_hr=116,
        ),
        make_lap(
            lap_number=2,
            distance_m=3.4,
            elapsed_time_sec=1,
            avg_hr=126,
        ),
        make_lap(
            lap_number=3,
            distance_m=1001.3,
            elapsed_time_sec=301,
            avg_hr=125,
        ),
        make_lap(
            lap_number=4,
            distance_m=995.9,
            elapsed_time_sec=759,
            moving_time_sec=293,
            avg_hr=121,
        ),
        make_lap(
            lap_number=5,
            distance_m=326.2,
            elapsed_time_sec=141,
            avg_hr=136,
        ),

        # Threshold block 1: 600 seconds
        make_lap(
            lap_number=6,
            distance_m=1000.4,
            elapsed_time_sec=246,
            avg_hr=151,
        ),
        make_lap(
            lap_number=7,
            distance_m=1004.5,
            elapsed_time_sec=246,
            avg_hr=161,
        ),
        make_lap(
            lap_number=8,
            distance_m=433.8,
            elapsed_time_sec=108,
            avg_hr=160,
        ),

        # Recovery 1: 91 seconds
        make_lap(
            lap_number=9,
            distance_m=249.7,
            elapsed_time_sec=91,
            avg_hr=152,
        ),

        # Threshold block 2: 599 seconds
        make_lap(
            lap_number=10,
            distance_m=990.9,
            elapsed_time_sec=244,
            avg_hr=158,
        ),
        make_lap(
            lap_number=11,
            distance_m=4.9,
            elapsed_time_sec=1,
            avg_hr=162,
        ),
        make_lap(
            lap_number=12,
            distance_m=1000.0,
            elapsed_time_sec=243,
            avg_hr=162,
        ),
        make_lap(
            lap_number=13,
            distance_m=454.8,
            elapsed_time_sec=111,
            avg_hr=163,
        ),

        # Recovery 2: 91 seconds
        make_lap(
            lap_number=14,
            distance_m=253.5,
            elapsed_time_sec=91,
            avg_hr=155,
        ),

        # Threshold block 3: 600 seconds
        make_lap(
            lap_number=15,
            distance_m=997.3,
            elapsed_time_sec=243,
            avg_hr=161,
        ),
        make_lap(
            lap_number=16,
            distance_m=3.3,
            elapsed_time_sec=1,
            avg_hr=166,
        ),
        make_lap(
            lap_number=17,
            distance_m=1000.2,
            elapsed_time_sec=244,
            avg_hr=165,
        ),
        make_lap(
            lap_number=18,
            distance_m=462.1,
            elapsed_time_sec=112,
            avg_hr=163,
        ),

        # Transition before cool-down: 90 seconds
        make_lap(
            lap_number=19,
            distance_m=260.8,
            elapsed_time_sec=90,
            avg_hr=157,
        ),

        # Cool-down
        make_lap(
            lap_number=20,
            distance_m=999.0,
            elapsed_time_sec=355,
            avg_hr=140,
        ),
        make_lap(
            lap_number=21,
            distance_m=4.1,
            elapsed_time_sec=1,
            avg_hr=144,
        ),
        make_lap(
            lap_number=22,
            distance_m=999.9,
            elapsed_time_sec=355,
            avg_hr=143,
        ),
        make_lap(
            lap_number=23,
            distance_m=512.3,
            elapsed_time_sec=167,
            avg_hr=143,
        ),
    ]


def test_detects_fast_finish_after_easy_running():
    analyzer = ExecutedWorkoutStructureAnalyzer()

    easy_laps = [
        make_lap(
            lap_number=index,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        )
        for index in range(1, 17)
    ]

    fast_last_lap = make_lap(
        lap_number=17,
        distance_m=1000,
        elapsed_time_sec=235,
        avg_hr=172,
    )

    result = analyzer._detect_fast_finish(
        easy_laps + [fast_last_lap]
    )

    assert result["detected"] is True
    assert result["laps"] == 1
    assert result["distance_km"] == 1.0

    assert (
        result["preceding_easy_distance_km"]
        == 16.0
    )

    assert (
        result["avg_pace_sec_per_km"]
        == 235.0
    )


def test_does_not_detect_fast_finish_when_last_lap_is_easy():
    analyzer = ExecutedWorkoutStructureAnalyzer()

    laps = [
        make_lap(
            lap_number=index,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        )
        for index in range(1, 18)
    ]

    result = analyzer._detect_fast_finish(laps)

    assert result["detected"] is False


def test_does_not_detect_fast_finish_without_substantial_easy_lead_in():
    analyzer = ExecutedWorkoutStructureAnalyzer()

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

    result = analyzer._detect_fast_finish(laps)

    assert result["detected"] is False


def test_detects_fast_finish_before_short_trailing_partial_lap():
    analyzer = ExecutedWorkoutStructureAnalyzer()

    laps = [
        make_lap(
            lap_number=index,
            distance_m=1000,
            elapsed_time_sec=330,
            avg_hr=140,
        )
        for index in range(1, 17)
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

    result = analyzer._detect_fast_finish(laps)

    assert result["detected"] is True
    assert result["lap_numbers"] == [17]
    assert result["distance_km"] == 1.0

    assert (
        result["trailing_partial_distance_km"]
        == 0.04
    )


def test_detects_three_threshold_blocks_split_by_autolaps():
    analyzer = ExecutedWorkoutStructureAnalyzer()

    laps = make_three_by_ten_threshold_laps()

    blocks = analyzer._find_threshold_blocks(laps)

    assert len(blocks) == 3

    assert [
        round(
            sum(
                lap.elapsed_time_sec
                for lap in block
            )
        )
        for block in blocks
    ] == [
        600,
        599,
        600,
    ]

    assert [
        [
            lap.lap_number
            for lap in block
        ]
        for block in blocks
    ] == [
        [6, 7, 8],
        [10, 11, 12, 13],
        [15, 16, 17, 18],
    ]


def test_preserves_threshold_workout_segment_order():
    """
    Measurement laps must not be confused with
    logical workout segments.

    Only gaps between threshold blocks count as
    inter-repetition recoveries.

    The 90-second lap after the final repetition is
    a transition into the cool-down, not a fourth
    recovery or another interval repetition.
    """

    analyzer = ExecutedWorkoutStructureAnalyzer()

    laps = make_three_by_ten_threshold_laps()

    threshold_blocks = analyzer._find_threshold_blocks(
        laps
    )

    segments = analyzer._build_ordered_threshold_segments(
        laps=laps,
        threshold_blocks=threshold_blocks,
    )

    assert [
        segment["segment"]
        for segment in segments
    ] == [
        "warmup",
        "threshold_block",
        "recovery",
        "threshold_block",
        "recovery",
        "threshold_block",
        "transition",
        "cooldown",
    ]

    assert [
        segment["lap_numbers"]
        for segment in segments
    ] == [
        [1, 2, 3, 4, 5],
        [6, 7, 8],
        [9],
        [10, 11, 12, 13],
        [14],
        [15, 16, 17, 18],
        [19],
        [20, 21, 22, 23],
    ]

    warmup = segments[0]
    cooldown = segments[-1]

    assert warmup["distance_km"] == 3.33
    assert cooldown["distance_km"] == 2.52

    threshold_segments = [
        segment
        for segment in segments
        if segment["segment"] == "threshold_block"
    ]

    assert [
        segment["duration_sec"]
        for segment in threshold_segments
    ] == [
        600,
        599,
        600,
    ]

    recovery_segments = [
        segment
        for segment in segments
        if segment["segment"] == "recovery"
    ]

    assert len(recovery_segments) == 2

    assert [
        segment["duration_sec"]
        for segment in recovery_segments
    ] == [
        91,
        91,
    ]

    assert segments[6]["duration_sec"] == 90

    # Every measurement lap belongs to exactly
    # one logical workout segment.
    assigned_laps = [
        number
        for segment in segments
        for number in segment["lap_numbers"]
    ]

    assert assigned_laps == list(range(1, 24))


def test_warmup_pace_uses_moving_time_not_elapsed_time():
    analyzer = ExecutedWorkoutStructureAnalyzer()

    laps = [
        make_lap(
            lap_number=1,
            distance_m=1000.5,
            elapsed_time_sec=325,
            moving_time_sec=325,
            avg_hr=116,
        ),
        make_lap(
            lap_number=2,
            distance_m=3.4,
            elapsed_time_sec=1,
            moving_time_sec=1,
            avg_hr=126,
        ),
        make_lap(
            lap_number=3,
            distance_m=1001.3,
            elapsed_time_sec=301,
            moving_time_sec=301,
            avg_hr=125,
        ),
        make_lap(
            lap_number=4,
            distance_m=995.9,
            elapsed_time_sec=759,
            moving_time_sec=293,
            avg_hr=121,
        ),
        make_lap(
            lap_number=5,
            distance_m=326.2,
            elapsed_time_sec=141,
            moving_time_sec=112,
            avg_hr=136,
        ),
    ]

    warmup = analyzer._build_ordered_segment(
        segment="warmup",
        laps=laps,
        intensity="easy",
    )

    assert warmup["distance_km"] == 3.33
    assert warmup["duration_sec"] == 1527
    assert warmup["moving_time_sec"] == 1032
    assert warmup["avg_pace_sec_per_km"] == 310.2


def test_warmup_does_not_infer_moving_time_when_missing():
    analyzer = ExecutedWorkoutStructureAnalyzer()

    laps = [
        make_lap(
            lap_number=1,
            distance_m=1000,
            elapsed_time_sec=330,
        ),
    ]

    warmup = analyzer._build_ordered_segment(
        segment="warmup",
        laps=laps,
        intensity="easy",
    )

    assert warmup["duration_sec"] == 330
    assert warmup["moving_time_sec"] is None
    assert warmup["avg_pace_sec_per_km"] is None 