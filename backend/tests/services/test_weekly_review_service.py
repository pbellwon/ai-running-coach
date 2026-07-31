from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pytest

import app.services.weekly_review_service as weekly_review_module
from app.services.composite_session_builder import (
    CompositeSessionBuilder,
)
from app.services.weekly_review_service import WeeklyReviewService


class FakeResolver:
    """
    Returns deterministic workout classifications based on source filename.
    """

    def __init__(self, classifications: dict[str, dict]):
        self.classifications = classifications

    def resolve(self, workout) -> dict:
        return self.classifications.get(
            workout.source_file,
            {
                "workout_type": "unknown",
                "confidence": 0.2,
                "classification_method": "fake_resolver",
                "warnings": [
                    f"No fake classification for {workout.source_file}."
                ],
            },
        )


def make_planned_workout(
    planned_date: date,
    workout_type: str,
    title: str,
    description: str | None = None,
    planned_distance_km: float | None = None,
    planned_duration_min: int | None = None,
    priority: str = "normal",
):
    return SimpleNamespace(
        planned_date=planned_date,
        workout_type=workout_type,
        title=title,
        description=description or title,
        planned_distance_km=planned_distance_km,
        planned_duration_min=planned_duration_min,
        priority=priority,
    )


def make_executed_workout(
    source_file: str,
    start_time: datetime,
    duration_min: float,
    distance_km: float | None,
    sport: str = "running",
):
    return SimpleNamespace(
        source_file=source_file,
        start_time=start_time,
        duration_sec=duration_min * 60,
        distance_km=distance_km,
        sport=sport,
    )


def build_review(
    monkeypatch: pytest.MonkeyPatch,
    planned_workouts: list,
    executed_workouts: list,
    classifications: dict[str, dict],
    week_start: str = "2025-06-02",
) -> dict:
    """
    Runs WeeklyReviewService with controlled plan and execution data.
    """

    service = WeeklyReviewService()

    monkeypatch.setattr(
        service,
        "_get_planned_workouts",
        lambda week_start, week_end: planned_workouts,
    )

    monkeypatch.setattr(
        service,
        "_get_executed_workouts",
        lambda week_start, week_end: executed_workouts,
    )

    resolver = FakeResolver(classifications)

    monkeypatch.setattr(
        weekly_review_module,
        "CompositeSessionBuilder",
        lambda: CompositeSessionBuilder(
            resolver=resolver,
        ),
    )

    return service.review(week_start)


def classification(
    workout_type: str,
    confidence: float = 0.9,
    method: str = "fake_resolver",
) -> dict:
    return {
        "workout_type": workout_type,
        "confidence": confidence,
        "classification_method": method,
        "warnings": [],
    }


def find_day(
    result: dict,
    day_date: str,
) -> dict:
    return next(
        day
        for day in result["days"]
        if day["date"] == day_date
    )


def test_single_session_is_executed_as_planned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [
        make_planned_workout(
            planned_date=date(2025, 6, 2),
            workout_type="easy_run",
            title="Easy",
        )
    ]

    executed = [
        make_executed_workout(
            source_file="easy.fit",
            start_time=datetime(2025, 6, 2, 17, 0),
            duration_min=50,
            distance_km=8,
        )
    ]

    result = build_review(
        monkeypatch=monkeypatch,
        planned_workouts=planned,
        executed_workouts=executed,
        classifications={
            "easy.fit": classification("easy_run"),
        },
    )

    summary = result["summary"]
    monday = find_day(result, "2025-06-02")

    assert summary["planned_training_count"] == 1
    assert summary["executed_source_activities_count"] == 1
    assert summary["executed_sessions_count"] == 1
    assert summary["paired_workouts_count"] == 1
    assert summary["type_matched_workouts_count"] == 1
    assert summary["type_mismatch_workouts_count"] == 0
    assert summary["missed_workouts_count"] == 0
    assert summary["unplanned_workouts_count"] == 0
    assert summary["execution_rate_percent"] == 100.0
    assert summary["type_compliance_rate_percent"] == 100.0

    assert monday["status"] == "executed_as_planned"

    session = monday["executed_sessions"][0]

    assert session["activities_count"] == 1
    assert session["workout_type"] == "easy_run"
    assert session["type_match"] is True
    assert session["components"][0]["role"] == "main"


def test_composite_session_groups_warmup_main_and_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [
        make_planned_workout(
            planned_date=date(2025, 6, 7),
            workout_type="tempo_run",
            title="Parkrun test",
            planned_distance_km=5,
            priority="key",
        )
    ]

    executed = [
        make_executed_workout(
            source_file="warmup.fit",
            start_time=datetime(2025, 6, 7, 8, 0),
            duration_min=20,
            distance_km=3,
        ),
        make_executed_workout(
            source_file="main.fit",
            start_time=datetime(2025, 6, 7, 8, 25),
            duration_min=20,
            distance_km=5,
        ),
        make_executed_workout(
            source_file="cooldown.fit",
            start_time=datetime(2025, 6, 7, 8, 50),
            duration_min=20,
            distance_km=3,
        ),
    ]

    result = build_review(
        monkeypatch=monkeypatch,
        planned_workouts=planned,
        executed_workouts=executed,
        classifications={
            "warmup.fit": classification(
                "easy_run+strides",
                confidence=0.75,
            ),
            "main.fit": classification(
                "tempo_run",
                confidence=0.8,
            ),
            "cooldown.fit": classification(
                "easy_run",
                confidence=0.7,
            ),
        },
    )

    summary = result["summary"]
    saturday = find_day(result, "2025-06-07")

    assert summary["executed_source_activities_count"] == 3
    assert summary["executed_sessions_count"] == 1
    assert summary["paired_workouts_count"] == 1
    assert summary["type_matched_workouts_count"] == 1
    assert summary["unplanned_workouts_count"] == 0

    assert saturday["status"] == "executed_as_planned"

    session = saturday["executed_sessions"][0]

    assert session["activities_count"] == 3
    assert session["workout_type"] == "tempo_run"
    assert session["total_distance_km"] == 11
    assert session["total_duration_min"] == 60
    assert session["classification_method"] == "composite_session"

    assert [
        component["role"]
        for component in session["components"]
    ] == [
        "warmup",
        "main",
        "cooldown",
    ]


def test_training_on_off_day_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [
        make_planned_workout(
            planned_date=date(2025, 6, 3),
            workout_type="off",
            title="off",
            priority="recovery",
        )
    ]

    executed = [
        make_executed_workout(
            source_file="unexpected-run.fit",
            start_time=datetime(2025, 6, 3, 18, 0),
            duration_min=45,
            distance_km=7,
        )
    ]

    result = build_review(
        monkeypatch=monkeypatch,
        planned_workouts=planned,
        executed_workouts=executed,
        classifications={
            "unexpected-run.fit": classification("easy_run"),
        },
    )

    summary = result["summary"]
    tuesday = find_day(result, "2025-06-03")

    assert summary["planned_training_count"] == 0
    assert summary["off_days_count"] == 1
    assert summary["trained_on_off_day_count"] == 1
    assert summary["executed_sessions_count"] == 1
    assert summary["unplanned_workouts_count"] == 1

    assert tuesday["status"] == "trained_on_off_day"
    assert (
        tuesday["planned_workouts"][0]["match_status"]
        == "off"
    )
    assert (
        tuesday["executed_sessions"][0]["matched_to_plan"]
        is False
    )


def test_missed_workout_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [
        make_planned_workout(
            planned_date=date(2025, 6, 4),
            workout_type="threshold",
            title="Threshold",
            priority="key",
        )
    ]

    result = build_review(
        monkeypatch=monkeypatch,
        planned_workouts=planned,
        executed_workouts=[],
        classifications={},
    )

    summary = result["summary"]
    wednesday = find_day(result, "2025-06-04")

    assert summary["planned_training_count"] == 1
    assert summary["executed_sessions_count"] == 0
    assert summary["paired_workouts_count"] == 0
    assert summary["missed_workouts_count"] == 1
    assert summary["execution_rate_percent"] == 0.0

    assert wednesday["status"] == "missed"
    assert (
        wednesday["planned_workouts"][0]["match_status"]
        == "missed"
    )


def test_two_separate_sessions_same_day_are_not_merged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [
        make_planned_workout(
            planned_date=date(2025, 6, 5),
            workout_type="easy_run",
            title="Easy",
        ),
        make_planned_workout(
            planned_date=date(2025, 6, 5),
            workout_type="strength",
            title="Strength",
        ),
    ]

    executed = [
        make_executed_workout(
            source_file="morning-run.fit",
            start_time=datetime(2025, 6, 5, 7, 0),
            duration_min=45,
            distance_km=8,
            sport="running",
        ),
        make_executed_workout(
            source_file="evening-strength.fit",
            start_time=datetime(2025, 6, 5, 18, 0),
            duration_min=50,
            distance_km=0,
            sport="training",
        ),
    ]

    result = build_review(
        monkeypatch=monkeypatch,
        planned_workouts=planned,
        executed_workouts=executed,
        classifications={
            "morning-run.fit": classification("easy_run"),
            "evening-strength.fit": classification(
                "strength",
                confidence=0.95,
                method="sport_mapping",
            ),
        },
    )

    summary = result["summary"]
    thursday = find_day(result, "2025-06-05")

    assert summary["executed_source_activities_count"] == 2
    assert summary["executed_sessions_count"] == 2
    assert summary["paired_workouts_count"] == 2
    assert summary["type_matched_workouts_count"] == 2
    assert summary["unplanned_workouts_count"] == 0
    assert summary["type_compliance_rate_percent"] == 100.0

    assert thursday["status"] == "executed_as_planned"

    matched_types = {
        session["matched_planned_type"]
        for session in thursday["executed_sessions"]
    }

    assert matched_types == {
        "easy_run",
        "strength",
    }


def test_type_mismatch_is_separate_from_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [
        make_planned_workout(
            planned_date=date(2025, 6, 6),
            workout_type="easy_run",
            title="Easy",
        )
    ]

    executed = [
        make_executed_workout(
            source_file="hard-run.fit",
            start_time=datetime(2025, 6, 6, 17, 0),
            duration_min=55,
            distance_km=12,
        )
    ]

    result = build_review(
        monkeypatch=monkeypatch,
        planned_workouts=planned,
        executed_workouts=executed,
        classifications={
            "hard-run.fit": classification(
                "vo2max",
                confidence=0.8,
            ),
        },
    )

    summary = result["summary"]
    friday = find_day(result, "2025-06-06")

    assert summary["paired_workouts_count"] == 1
    assert summary["type_matched_workouts_count"] == 0
    assert summary["type_mismatch_workouts_count"] == 1

    # A workout was performed, so execution is 100%.
    assert summary["execution_rate_percent"] == 100.0

    # But it was the wrong workout type.
    assert summary["type_compliance_rate_percent"] == 0.0
    assert (
        summary["paired_type_compliance_rate_percent"]
        == 0.0
    )

    assert friday["status"] == "executed_type_mismatch"

    planned_entry = friday["planned_workouts"][0]
    executed_session = friday["executed_sessions"][0]

    assert planned_entry["match_status"] == "type_mismatch"
    assert planned_entry["matched_executed_type"] == "vo2max"
    assert planned_entry["type_match"] is False

    assert executed_session["matched_to_plan"] is True
    assert executed_session["matched_planned_type"] == "easy_run"
    assert executed_session["workout_type"] == "vo2max"
    assert executed_session["type_match"] is False


def test_invalid_week_start_must_be_monday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WeeklyReviewService()

    with pytest.raises(
        ValueError,
        match="week_start must be a Monday",
    ):
        service.review("2025-06-03")