from __future__ import annotations

from datetime import date, datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import WorkoutDB
from app.models.goal import Goal
from app.models.goal_progress import GoalProgress
from app.services.composite_session_builder import (
    CompositeSessionBuilder,
)
from app.services.goal_progress_engine import (
    GoalProgressEngine,
)


class GoalProgressService:
    """
    Production-facing service for Goal Progress.

    Loads two consecutive 28-day windows from the database,
    converts raw workouts into logical sessions and delegates
    deterministic analysis to GoalProgressEngine.
    """

    WINDOW_DAYS = 28

    def build(
        self,
        goal: Goal,
        target_date: date | datetime | str,
    ) -> GoalProgress:
        normalized_date = self._normalize_date(
            target_date
        )

        recent_start = (
            normalized_date
            - timedelta(
                days=self.WINDOW_DAYS - 1
            )
        )

        previous_end = (
            recent_start
            - timedelta(days=1)
        )

        previous_start = (
            previous_end
            - timedelta(
                days=self.WINDOW_DAYS - 1
            )
        )

        workouts = self._get_workouts(
            start_date=previous_start,
            end_date=normalized_date,
        )

        sessions = (
            CompositeSessionBuilder()
            .build(workouts)
        )

        recent_sessions = [
            session
            for session in sessions
            if (
                recent_start
                <= session.start_time.date()
                <= normalized_date
            )
        ]

        previous_sessions = [
            session
            for session in sessions
            if (
                previous_start
                <= session.start_time.date()
                <= previous_end
            )
        ]

        return GoalProgressEngine().analyze(
            goal=goal,
            target_date=normalized_date,
            recent_sessions=recent_sessions,
            previous_sessions=previous_sessions,
        )

    def _get_workouts(
        self,
        start_date: date,
        end_date: date,
    ) -> list[WorkoutDB]:
        range_start = datetime.combine(
            start_date,
            datetime.min.time(),
        )

        range_end = datetime.combine(
            end_date
            + timedelta(days=1),
            datetime.min.time(),
        )

        db = SessionLocal()

        try:
            return (
                db.query(WorkoutDB)
                .filter(
                    WorkoutDB.start_time
                    >= range_start
                )
                .filter(
                    WorkoutDB.start_time
                    < range_end
                )
                .order_by(
                    WorkoutDB.start_time.asc()
                )
                .all()
            )

        finally:
            db.close()

    def _normalize_date(
        self,
        value: date | datetime | str,
    ) -> date:
        if isinstance(
            value,
            datetime,
        ):
            return value.date()

        if isinstance(
            value,
            date,
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            normalized = value.strip()

            try:
                return date.fromisoformat(
                    normalized
                )

            except ValueError as exc:
                raise ValueError(
                    "Date must use "
                    "YYYY-MM-DD format."
                ) from exc

        raise TypeError(
            "Date must be date, "
            "datetime or ISO string."
        )