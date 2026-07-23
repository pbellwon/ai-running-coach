from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.services.plan_matcher import PlanMatcher


@pytest.fixture
def matcher() -> PlanMatcher:
    return PlanMatcher()


@pytest.fixture
def planned_workouts() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            planned_date=date(2024, 11, 11),
            title="Race",
        ),
        SimpleNamespace(
            planned_date="2024-11-12",
            title="Off",
        ),
        SimpleNamespace(
            planned_date=datetime(2024, 11, 13, 8, 30),
            title="Easy",
        ),
    ]


def test_match_by_date_returns_matching_workout(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    result = matcher.match_by_date(
        executed_date="2024-11-11",
        planned_workouts=planned_workouts,
    )

    assert result is not None
    assert result.title == "Race"
    assert result.planned_date == date(2024, 11, 11)


def test_match_by_date_returns_none_when_date_is_missing(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    result = matcher.match_by_date(
        executed_date="2030-01-01",
        planned_workouts=planned_workouts,
    )

    assert result is None


def test_match_by_date_accepts_datetime(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    result = matcher.match_by_date(
        executed_date=datetime(2024, 11, 13, 18, 45),
        planned_workouts=planned_workouts,
    )

    assert result is not None
    assert result.title == "Easy"


def test_match_extracts_date_from_object(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    executed_workout = SimpleNamespace(
        start_time=datetime(2024, 11, 11, 9, 15),
    )

    result = matcher.match(
        executed_workout=executed_workout,
        planned_workouts=planned_workouts,
    )

    assert result is not None
    assert result.title == "Race"


def test_match_extracts_date_from_dictionary(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    executed_workout = {
        "activity_date": "2024-11-12T17:30:00",
    }

    result = matcher.match(
        executed_workout=executed_workout,
        planned_workouts=planned_workouts,
    )

    assert result is not None
    assert result.title == "Off"


def test_match_raises_error_when_executed_date_is_missing(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    executed_workout = SimpleNamespace(
        title="Workout without date",
    )

    with pytest.raises(
        ValueError,
        match="Cannot determine executed workout date",
    ):
        matcher.match(
            executed_workout=executed_workout,
            planned_workouts=planned_workouts,
        )


def test_match_by_date_rejects_invalid_date_format(
    matcher: PlanMatcher,
    planned_workouts: list[SimpleNamespace],
) -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported workout date format",
    ):
        matcher.match_by_date(
            executed_date="11.11.2024",
            planned_workouts=planned_workouts,
        )


def test_match_by_date_returns_first_workout_when_date_is_duplicated(
    matcher: PlanMatcher,
) -> None:
    planned_workouts = [
        SimpleNamespace(
            planned_date="2024-11-11",
            title="Morning run",
        ),
        SimpleNamespace(
            planned_date="2024-11-11",
            title="Evening mobility",
        ),
    ]

    result = matcher.match_by_date(
        executed_date="2024-11-11",
        planned_workouts=planned_workouts,
    )

    assert result is not None
    assert result.title == "Morning run"