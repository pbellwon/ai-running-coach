from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from app.models.planned_workout import PlannedWorkout


class PlanMatcher:
    """
    Matches an executed workout to a planned workout.

    Sprint 17 implementation:
    - exact calendar-date matching only;
    - no fuzzy matching;
    - no matching by workout type;
    - no support for shifted workouts yet.
    """

    def match(
        self,
        executed_workout: Any,
        planned_workouts: Iterable[PlannedWorkout],
    ) -> PlannedWorkout | None:
        executed_date = self._extract_executed_date(executed_workout)

        return self.match_by_date(
            executed_date=executed_date,
            planned_workouts=planned_workouts,
        )

    def match_by_date(
        self,
        executed_date: date | datetime | str,
        planned_workouts: Iterable[PlannedWorkout],
    ) -> PlannedWorkout | None:
        normalized_executed_date = self._normalize_date(executed_date)

        for planned_workout in planned_workouts:
            planned_date = self._normalize_date(
                planned_workout.planned_date
            )

            if planned_date == normalized_executed_date:
                return planned_workout

        return None

    def _extract_executed_date(self, executed_workout: Any) -> date:
        """
        Supports the common date fields used by workout importers.

        The first available field is used.
        """

        candidate_fields = [
            "workout_date",
            "activity_date",
            "start_date",
            "start_time",
            "started_at",
            "date",
        ]

        for field_name in candidate_fields:
            value = getattr(executed_workout, field_name, None)

            if value is not None:
                return self._normalize_date(value)

        if isinstance(executed_workout, dict):
            for field_name in candidate_fields:
                value = executed_workout.get(field_name)

                if value is not None:
                    return self._normalize_date(value)

        raise ValueError(
            "Cannot determine executed workout date. "
            f"Expected one of: {', '.join(candidate_fields)}."
        )

    def _normalize_date(
        self,
        value: date | datetime | str,
    ) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            normalized_value = value.strip()

            if not normalized_value:
                raise ValueError("Workout date cannot be empty.")

            try:
                return date.fromisoformat(normalized_value)
            except ValueError:
                pass

            iso_datetime = normalized_value.replace("Z", "+00:00")

            try:
                return datetime.fromisoformat(iso_datetime).date()
            except ValueError as exc:
                raise ValueError(
                    f"Unsupported workout date format: {value!r}."
                ) from exc

        raise TypeError(
            "Workout date must be a date, datetime or ISO string. "
            f"Received: {type(value).__name__}."
        )