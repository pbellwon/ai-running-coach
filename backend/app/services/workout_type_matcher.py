from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.planned_workout import PlannedWorkout


@dataclass
class WorkoutTypeMatch:
    planned_workout: PlannedWorkout
    executed_workout: Any
    planned_type: str
    executed_type: str
    type_match: bool
    match_score: int


class WorkoutTypeMatcher:
    """
    Matches planned and executed workouts within the same calendar day.

    Matching priorities:
    1. exact workout-type match;
    2. compatible workout-type match;
    3. fallback match when executed type is unknown;
    4. unmatched planned and executed workouts remain separate.
    """

    def match_day(
        self,
        planned_workouts: list[PlannedWorkout],
        executed_workouts: list[Any],
        executed_types: dict[str, dict],
    ) -> dict:
        remaining_planned = list(planned_workouts)
        remaining_executed = list(executed_workouts)

        matches: list[WorkoutTypeMatch] = []

        candidates: list[tuple[int, int, int, bool]] = []

        for planned_index, planned_workout in enumerate(
            remaining_planned
        ):
            for executed_index, executed_workout in enumerate(
                remaining_executed
            ):
                source_file = getattr(
                    executed_workout,
                    "source_file",
                    None,
                )

                type_result = executed_types.get(
                    source_file,
                    {},
                )

                executed_type = type_result.get(
                    "workout_type",
                    "unknown",
                )

                score, type_match = self._calculate_score(
                    planned_type=planned_workout.workout_type,
                    executed_type=executed_type,
                )

                candidates.append(
                    (
                        score,
                        planned_index,
                        executed_index,
                        type_match,
                    )
                )

        candidates.sort(
            key=lambda candidate: candidate[0],
            reverse=True,
        )

        used_planned_indexes: set[int] = set()
        used_executed_indexes: set[int] = set()

        for (
            score,
            planned_index,
            executed_index,
            type_match,
        ) in candidates:
            if score <= 0:
                continue

            if planned_index in used_planned_indexes:
                continue

            if executed_index in used_executed_indexes:
                continue

            planned_workout = remaining_planned[
                planned_index
            ]

            executed_workout = remaining_executed[
                executed_index
            ]

            source_file = getattr(
                executed_workout,
                "source_file",
                None,
            )

            executed_type = executed_types.get(
                source_file,
                {},
            ).get(
                "workout_type",
                "unknown",
            )

            matches.append(
                WorkoutTypeMatch(
                    planned_workout=planned_workout,
                    executed_workout=executed_workout,
                    planned_type=planned_workout.workout_type,
                    executed_type=executed_type,
                    type_match=type_match,
                    match_score=score,
                )
            )

            used_planned_indexes.add(planned_index)
            used_executed_indexes.add(executed_index)

        unmatched_planned = [
            workout
            for index, workout in enumerate(
                remaining_planned
            )
            if index not in used_planned_indexes
        ]

        unmatched_executed = [
            workout
            for index, workout in enumerate(
                remaining_executed
            )
            if index not in used_executed_indexes
        ]

        return {
            "matches": matches,
            "unmatched_planned": unmatched_planned,
            "unmatched_executed": unmatched_executed,
        }

    def _calculate_score(
        self,
        planned_type: str,
        executed_type: str,
    ) -> tuple[int, bool]:
        normalized_planned = self._normalize_type(
            planned_type
        )

        normalized_executed = self._normalize_type(
            executed_type
        )

        if normalized_planned == "off":
            return 0, False

        if normalized_planned == normalized_executed:
            return 100, True

        if self._types_are_compatible(
            planned_type=normalized_planned,
            executed_type=normalized_executed,
        ):
            return 80, True

        if normalized_executed == "unknown":
            return 20, False

        return 10, False

    def _types_are_compatible(
        self,
        planned_type: str,
        executed_type: str,
    ) -> bool:
        compatible_types = {
            "easy_run": {
                "easy_run",
                "easy_run+strides",
            },
            "easy_run+strides": {
                "easy_run+strides",
            },
            "easy_run+hills": {
                "easy_run+hills",
                "easy_run",
            },
            "tempo_run": {
                "tempo_run",
                "threshold",
            },
            "threshold": {
                "threshold",
                "tempo_run",
            },
            "vo2max": {
                "vo2max",
                "intervals",
            },
            "intervals": {
                "intervals",
                "vo2max",
            },
            "long_run": {
                "long_run",
                "easy_run",
            },
            "race": {
                "race",
                "threshold",
                "vo2max",
            },
            "strength": {
                "strength",
            },
            "bike": {
                "bike",
            },
            "swimming": {
                "swimming",
            },
            "mobility": {
                "mobility",
            },
        }

        allowed_executed_types = compatible_types.get(
            planned_type,
            set(),
        )

        return executed_type in allowed_executed_types

    def _normalize_type(
        self,
        value: str | None,
    ) -> str:
        if value is None:
            return "unknown"

        return value.strip().lower()