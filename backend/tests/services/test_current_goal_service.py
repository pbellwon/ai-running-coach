from datetime import date

from app.models.goal import Goal
from app.services.current_goal_service import (
    CurrentGoalService,
)


def test_returns_current_primary_goal():
    goal = CurrentGoalService().get()

    assert isinstance(
        goal,
        Goal,
    )

    assert (
        goal.goal_type
        == "race_time"
    )

    assert (
        goal.distance_km
        == 10
    )

    assert (
        goal.target_time_sec
        == 2310
    )

    assert (
        goal.target_date
        == date(
            2026,
            11,
            11,
        )
    )

    assert (
        goal.priority
        == "A"
    )

    assert (
        goal.notes
        == (
            "Target 38:30 for 10K "
            "in Gdynia."
        )
    )