from __future__ import annotations

from app.analysis.executed_workout_structure_analyzer import (
    ExecutedWorkoutStructureAnalyzer,
)
from app.db.models import WorkoutDB


class ExecutedWorkoutTypeResolver:
    """
    Resolves the semantic type of an executed workout.

    Running workouts are classified using lap and structure analysis.
    Other sports are resolved primarily from WorkoutDB.sport.
    """

    def resolve(
        self,
        workout: WorkoutDB,
    ) -> dict:
        sport = self._normalize_sport(workout.sport)

        if sport == "running":
            return self._resolve_running(workout)

        if sport == "training":
            return {
                "workout_type": "strength",
                "confidence": 0.95,
                "classification_method": "sport_mapping",
                "warnings": [],
            }

        if sport == "cycling":
            return {
                "workout_type": "bike",
                "confidence": 0.95,
                "classification_method": "sport_mapping",
                "warnings": [],
            }

        if sport == "swimming":
            return {
                "workout_type": "swimming",
                "confidence": 0.95,
                "classification_method": "sport_mapping",
                "warnings": [],
            }

        if sport in {
            "walking",
            "hiking",
            "mountaineering",
        }:
            return {
                "workout_type": "low_intensity_cross_training",
                "confidence": 0.85,
                "classification_method": "sport_mapping",
                "warnings": [],
            }

        if sport == "fitness_equipment":
            return {
                "workout_type": "cross_training",
                "confidence": 0.8,
                "classification_method": "sport_mapping",
                "warnings": [
                    "Fitness equipment activity type is not specific."
                ],
            }

        if sport in {
            "stand_up_paddleboarding",
            "surfing",
            "kayaking",
        }:
            return {
                "workout_type": "other_endurance",
                "confidence": 0.8,
                "classification_method": "sport_mapping",
                "warnings": [],
            }

        return {
            "workout_type": "unknown",
            "confidence": 0.2,
            "classification_method": "sport_mapping",
            "warnings": [
                f"Unsupported executed sport: {sport or 'missing'}."
            ],
        }

    def _resolve_running(
        self,
        workout: WorkoutDB,
    ) -> dict:
        if not workout.source_file:
            return {
                "workout_type": "unknown",
                "confidence": 0.2,
                "classification_method": "missing_source_file",
                "warnings": [
                    "Running workout has no source file."
                ],
            }

        analysis = ExecutedWorkoutStructureAnalyzer().analyze(
            workout.source_file
        )

        summary = analysis.get("summary", {})

        return {
            "workout_type": summary.get(
                "detected_type",
                "unknown",
            ),
            "confidence": summary.get(
                "confidence",
                0,
            ),
            "classification_method": summary.get(
                "classification_method",
                "unknown",
            ),
            "warnings": list(
                summary.get("warnings", [])
            ),
        }

    def _normalize_sport(
        self,
        value: str | None,
    ) -> str:
        if value is None:
            return ""

        return value.strip().lower()