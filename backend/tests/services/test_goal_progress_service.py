from datetime import date, datetime

from app.models.goal import Goal
from app.services.goal_progress_service import (
    GoalProgressService,
)


def test_goal_progress_service_builds_progress_from_database(
    monkeypatch,
):
    service = GoalProgressService()

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    class Workout:
        def __init__(
            self,
            source_file,
            start_time,
            sport,
            distance_km,
            duration_sec,
            declared_workout_type,
        ):
            self.source_file = source_file
            self.start_time = start_time
            self.sport = sport
            self.distance_km = distance_km
            self.duration_sec = duration_sec

            self.avg_hr = None
            self.max_hr = None
            self.avg_pace_sec_per_km = None
            self.records_count = None
            self.laps_count = None
            self.activity_name = None
            self.description = None
            self.external_type = None
            self.source_platform = None
            self.training_load = None
            self.rpe = None
            self.race = None
            self.interval_summary = None

            self.declared_workout_type = (
                declared_workout_type
            )

            self.declared_session_role = None

    workouts = [
        Workout(
            source_file="previous-easy",
            start_time=datetime(
                2026,
                7,
                10,
                17,
                0,
            ),
            sport="running",
            distance_km=10,
            duration_sec=3300,
            declared_workout_type="easy_run",
        ),
        Workout(
            source_file="previous-long",
            start_time=datetime(
                2026,
                7,
                12,
                9,
                0,
            ),
            sport="running",
            distance_km=15,
            duration_sec=5100,
            declared_workout_type="easy_run",
        ),
        Workout(
            source_file="recent-easy",
            start_time=datetime(
                2026,
                8,
                1,
                17,
                0,
            ),
            sport="running",
            distance_km=14,
            duration_sec=4620,
            declared_workout_type="easy_run",
        ),
        Workout(
            source_file="recent-long",
            start_time=datetime(
                2026,
                8,
                8,
                9,
                0,
            ),
            sport="running",
            distance_km=18,
            duration_sec=6000,
            declared_workout_type="easy_run",
        ),
    ]

    monkeypatch.setattr(
        service,
        "_get_workouts",
        lambda start_date, end_date: workouts,
    )

    result = service.build(
        goal=goal,
        target_date="2026-08-10",
    )

    assert result.target_date == date(
        2026,
        8,
        10,
    )

    assert result.goal_distance_km == 10
    assert result.target_time_sec == 2310

    assert len(result.capabilities) == 5

    aerobic = next(
        capability
        for capability in result.capabilities
        if capability.area == "aerobic_base"
    )

    long_run = next(
        capability
        for capability in result.capabilities
        if capability.area
        == "long_run_durability"
    )

    assert aerobic.status == "improving"
    assert long_run.status == "improving"

    assert result.status == "progressing"