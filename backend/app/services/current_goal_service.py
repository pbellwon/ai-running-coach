from __future__ import annotations

from datetime import date

from app.models.goal import Goal


class CurrentGoalService:
    """
    Single source of truth for the athlete's
    current primary training goal.

    This is intentionally simple for the MVP.
    Later the goal can be persisted in the database
    without changing downstream services.
    """

    def get(self) -> Goal:
        return Goal(
            goal_type="race_time",
            distance_km=10,
            target_time_sec=2310,
            target_date=date(
                2026,
                11,
                11,
            ),
            priority="A",
            notes=(
                "Target 38:30 for 10K "
                "in Gdynia."
            ),
        )