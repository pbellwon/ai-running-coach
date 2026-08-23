from __future__ import annotations

from app.db.models import WorkoutDB


class ExecutedWorkoutTypeResolver:
    """
    Resolves the executed workout type for a WorkoutDB activity.

    Priority:

    1. Intervals.icu declared_workout_type
    2. Non-running sport mapping
    3. Running heuristics based on available summary data
    4. unknown fallback

    Important:
    declared_session_role is intentionally NOT returned as
    workout_type.

    Example:
        "Long tempo"

        declared_workout_type = tempo_run
        declared_session_role = long_run

    The resolver returns the physiological workout type.
    Session role is handled separately.
    """

    def resolve(
        self,
        workout: WorkoutDB,
    ) -> dict:
        declared_type = getattr(
            workout,
            "declared_workout_type",
            None,
        )

        if declared_type:
            return {
                "workout_type": declared_type,
                "confidence": 0.9,
                "classification_method": (
                    "intervals_declared_type"
                ),
                "warnings": [],
            }

        sport_result = self._resolve_by_sport(
            workout
        )

        if sport_result is not None:
            return sport_result

        if workout.sport == "running":
            return self._resolve_running(
                workout
            )

        return self._unknown(
            warning=(
                "Unable to classify workout "
                "from available activity data."
            )
        )

    def _resolve_by_sport(
        self,
        workout: WorkoutDB,
    ) -> dict | None:
        sport = (
            workout.sport or ""
        ).strip().lower()

        if sport == "training":
            return {
                "workout_type": "strength",
                "confidence": 0.95,
                "classification_method": (
                    "sport_mapping"
                ),
                "warnings": [],
            }

        if sport == "cycling":
            return {
                "workout_type": "bike",
                "confidence": 0.95,
                "classification_method": (
                    "sport_mapping"
                ),
                "warnings": [],
            }

        if sport == "swimming":
            return {
                "workout_type": "swimming",
                "confidence": 0.95,
                "classification_method": (
                    "sport_mapping"
                ),
                "warnings": [],
            }

        if sport == "walking":
            return {
                "workout_type": "walking",
                "confidence": 0.95,
                "classification_method": (
                    "sport_mapping"
                ),
                "warnings": [],
            }

        if sport == "hiking":
            return {
                "workout_type": "hiking",
                "confidence": 0.95,
                "classification_method": (
                    "sport_mapping"
                ),
                "warnings": [],
            }

        return None

    def _resolve_running(
        self,
        workout: WorkoutDB,
    ) -> dict:
        """
        Fallback classification for running activities when
        no declared workout type is available.

        Current Intervals.icu activities should normally be
        classified through declared_workout_type.

        These heuristics mainly preserve compatibility with
        older FIT-based imports.
        """

        avg_hr = self._to_float(
            workout.avg_hr
        )

        max_hr = self._to_float(
            workout.max_hr
        )

        pace = self._to_float(
            workout.avg_pace_sec_per_km
        )

        laps_count = self._to_int(
            workout.laps_count
        )

        distance_km = self._to_float(
            workout.distance_km
        )

        duration_sec = self._to_float(
            workout.duration_sec
        )

        declared_session_role = getattr(
            workout,
            "declared_session_role",
            None,
        )

        warnings = [
            "Classification based only on executed summary data."
        ]

        if declared_session_role == "long_run":
            if self._looks_like_tempo(
                laps_count=laps_count,
                avg_hr=avg_hr,
                pace=pace,
                distance_km=distance_km,
                duration_sec=duration_sec,
            ):
                return {
                    "workout_type": "tempo_run",
                    "confidence": 0.7,
                    "classification_method": (
                        "long_run_summary"
                    ),
                    "warnings": warnings,
                }

            return {
                "workout_type": "easy_run",
                "confidence": 0.8,
                "classification_method": (
                    "declared_session_role"
                ),
                "warnings": [],
            }

        if self._looks_like_vo2max(
            laps_count=laps_count,
            avg_hr=avg_hr,
            max_hr=max_hr,
            distance_km=distance_km,
            duration_sec=duration_sec,
        ):
            return {
                "workout_type": "vo2max",
                "confidence": 0.6,
                "classification_method": (
                    "lap_pattern"
                ),
                "warnings": warnings
                + [
                    "VO2max classification is estimated "
                    "from short fast repetitions."
                ],
            }

        if self._looks_like_tempo(
            laps_count=laps_count,
            avg_hr=avg_hr,
            pace=pace,
            distance_km=distance_km,
            duration_sec=duration_sec,
        ):
            return {
                "workout_type": "tempo_run",
                "confidence": 0.7,
                "classification_method": (
                    "lap_pattern"
                ),
                "warnings": warnings
                + [
                    "Tempo effort detected from "
                    "summary characteristics."
                ],
            }

        if self._looks_like_easy_run(
            avg_hr=avg_hr,
            distance_km=distance_km,
            duration_sec=duration_sec,
        ):
            return {
                "workout_type": "easy_run",
                "confidence": 0.65,
                "classification_method": (
                    "summary_pattern"
                ),
                "warnings": warnings,
            }

        return self._unknown(
            warning=(
                "Running activity could not be "
                "classified reliably."
            )
        )

    def _looks_like_vo2max(
        self,
        laps_count: int | None,
        avg_hr: float | None,
        max_hr: float | None,
        distance_km: float | None,
        duration_sec: float | None,
    ) -> bool:
        if (
            laps_count is None
            or laps_count < 6
        ):
            return False

        if (
            duration_sec is None
            or duration_sec < 20 * 60
        ):
            return False

        if (
            distance_km is not None
            and distance_km >= 15
        ):
            return False

        if (
            max_hr is None
            or avg_hr is None
        ):
            return False

        if max_hr - avg_hr < 12:
            return False

        if avg_hr < 145:
            return False

        return True

    def _looks_like_tempo(
        self,
        laps_count: int | None,
        avg_hr: float | None,
        pace: float | None,
        distance_km: float | None,
        duration_sec: float | None,
    ) -> bool:
        if (
            distance_km is None
            or distance_km < 4
        ):
            return False

        if (
            duration_sec is None
            or duration_sec < 20 * 60
        ):
            return False

        if (
            laps_count is not None
            and 3 <= laps_count <= 10
            and avg_hr is not None
            and avg_hr >= 145
        ):
            return True

        if (
            pace is not None
            and pace <= 300
            and avg_hr is not None
            and avg_hr >= 145
        ):
            return True

        return False

    def _looks_like_easy_run(
        self,
        avg_hr: float | None,
        distance_km: float | None,
        duration_sec: float | None,
    ) -> bool:
        if (
            distance_km is None
            or distance_km <= 0
        ):
            return False

        if (
            duration_sec is None
            or duration_sec < 15 * 60
        ):
            return False

        if avg_hr is None:
            return True

        return avg_hr < 150

    def _unknown(
        self,
        warning: str,
    ) -> dict:
        return {
            "workout_type": "unknown",
            "confidence": 0.0,
            "classification_method": "fallback",
            "warnings": [
                warning
            ],
        }

    def _to_float(
        self,
        value,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(
        self,
        value,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None