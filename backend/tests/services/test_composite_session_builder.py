from datetime import datetime
from types import SimpleNamespace

from app.services.composite_session_builder import (
    CompositeSessionBuilder,
)


class FakeResolver:
    def __init__(self, types: dict[str, dict]):
        self.types = types

    def resolve(self, workout):
        return self.types[workout.source_file]


def make_workout(
    source_file: str,
    start_time: datetime,
    duration_min: float,
    distance_km: float,
    sport: str = "running",
):
    return SimpleNamespace(
        source_file=source_file,
        start_time=start_time,
        duration_sec=duration_min * 60,
        distance_km=distance_km,
        sport=sport,
    )


def test_builds_single_activity_session():
    workout = make_workout(
        source_file="easy.fit",
        start_time=datetime(2025, 6, 4, 13, 30),
        duration_min=50,
        distance_km=7.5,
    )

    resolver = FakeResolver(
        {
            "easy.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            }
        }
    )

    builder = CompositeSessionBuilder(
        resolver=resolver
    )

    sessions = builder.build([workout])

    assert len(sessions) == 1

    session = sessions[0]

    assert session.workout_type == "easy_run"
    assert session.activities_count == 1
    assert session.total_distance_km == 7.5
    assert session.components[0].role == "main"


def test_groups_warmup_race_and_cooldown():
    warmup = make_workout(
        source_file="warmup.fit",
        start_time=datetime(2025, 6, 7, 6, 35),
        duration_min=22.8,
        distance_km=2.95,
    )

    race = make_workout(
        source_file="race.fit",
        start_time=datetime(2025, 6, 7, 7, 2),
        duration_min=21.5,
        distance_km=4.97,
    )

    cooldown = make_workout(
        source_file="cooldown.fit",
        start_time=datetime(2025, 6, 7, 7, 27),
        duration_min=19.3,
        distance_km=3.05,
    )

    resolver = FakeResolver(
        {
            "warmup.fit": {
                "workout_type": "easy_run+strides",
                "confidence": 0.75,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
            "race.fit": {
                "workout_type": "tempo_run",
                "confidence": 0.70,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
            "cooldown.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
        }
    )

    builder = CompositeSessionBuilder(
        resolver=resolver
    )

    sessions = builder.build(
        [warmup, race, cooldown]
    )

    assert len(sessions) == 1

    session = sessions[0]

    assert session.activities_count == 3
    assert session.workout_type == "tempo_run"
    assert session.total_distance_km == 10.97
    assert session.total_duration_min == 63.6

    assert [
        component.role
        for component in session.components
    ] == [
        "warmup",
        "main",
        "cooldown",
    ]


def test_does_not_group_running_sessions_hours_apart():
    morning = make_workout(
        source_file="morning.fit",
        start_time=datetime(2025, 6, 7, 7, 0),
        duration_min=45,
        distance_km=8,
    )

    evening = make_workout(
        source_file="evening.fit",
        start_time=datetime(2025, 6, 7, 17, 0),
        duration_min=40,
        distance_km=7,
    )

    resolver = FakeResolver(
        {
            "morning.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
            "evening.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
        }
    )

    builder = CompositeSessionBuilder(
        resolver=resolver
    )

    sessions = builder.build(
        [morning, evening]
    )

    assert len(sessions) == 2


def test_does_not_group_strength_and_running():
    strength = make_workout(
        source_file="strength.fit",
        start_time=datetime(2025, 6, 2, 14, 0),
        duration_min=45,
        distance_km=0,
        sport="training",
    )

    running = make_workout(
        source_file="run.fit",
        start_time=datetime(2025, 6, 2, 15, 0),
        duration_min=40,
        distance_km=7,
        sport="running",
    )

    resolver = FakeResolver(
        {
            "strength.fit": {
                "workout_type": "strength",
                "confidence": 0.95,
                "classification_method": "sport_mapping",
                "warnings": [],
            },
            "run.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
        }
    )

    builder = CompositeSessionBuilder(
        resolver=resolver
    )

    sessions = builder.build(
        [strength, running]
    )

    assert len(sessions) == 2

    assert sessions[0].workout_type == "strength"
    assert sessions[1].workout_type == "easy_run"


def test_does_not_merge_two_substantial_easy_runs():
    first = make_workout(
        source_file="first.fit",
        start_time=datetime(2025, 6, 7, 7, 0),
        duration_min=50,
        distance_km=9,
    )

    second = make_workout(
        source_file="second.fit",
        start_time=datetime(2025, 6, 7, 8, 0),
        duration_min=45,
        distance_km=8,
    )

    resolver = FakeResolver(
        {
            "first.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
            "second.fit": {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": "lap_pattern",
                "warnings": [],
            },
        }
    )

    builder = CompositeSessionBuilder(
        resolver=resolver
    )

    sessions = builder.build(
        [first, second]
    )

    assert len(sessions) == 2