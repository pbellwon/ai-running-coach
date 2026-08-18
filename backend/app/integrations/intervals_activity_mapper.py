from __future__ import annotations

import json
from datetime import datetime

from app.db.models import WorkoutDB
from app.services.intervals_declared_type_classifier import (
    IntervalsDeclaredTypeClassifier,
)


class IntervalsActivityMapper:
    """
    Maps Intervals.icu activity data into WorkoutDB.

    Intervals metadata is preserved so that PaceMind can classify
    current activities without requiring downloaded FIT files.
    """

    SOURCE_PREFIX = "intervals_icu"

    SPORT_MAPPING = {
        "Run": "running",
        "Ride": "cycling",
        "VirtualRide": "cycling",
        "Swim": "swimming",
        "WeightTraining": "training",
        "Workout": "training",
        "Hike": "hiking",
        "Walk": "walking",
    }

    def __init__(
        self,
        declared_type_classifier: (
            IntervalsDeclaredTypeClassifier | None
        ) = None,
    ):
        self.declared_type_classifier = (
            declared_type_classifier
            or IntervalsDeclaredTypeClassifier()
        )

    def map(
        self,
        activity: dict,
    ) -> WorkoutDB:
        activity_id = activity.get("id")

        if not activity_id:
            raise ValueError(
                "Intervals activity is missing id."
            )

        activity_name = self._to_string(
            activity.get("name")
        )

        description = self._to_string(
            activity.get("description")
        )

        external_type = self._to_string(
            activity.get("type")
        )

        race = self._to_bool(
            activity.get("race")
        )

        declared_classification = (
            self.declared_type_classifier.classify(
            name=activity_name,
            description=description,
            race=race,
            external_type=external_type,
            )
        )

        distance_km = self._meters_to_km(
            activity.get("distance")
        )

        duration_sec = self._get_duration_sec(
            activity
        )

        return WorkoutDB(
            source_file=self.build_source_key(
                activity_id
            ),
            start_time=self._parse_start_time(
                activity.get("start_date_local")
            ),
            sport=self._map_sport(
                external_type
            ),
            distance_km=distance_km,
            duration_sec=duration_sec,
            avg_hr=self._to_float(
                activity.get("average_heartrate")
            ),
            max_hr=self._to_float(
                activity.get("max_heartrate")
            ),
            avg_pace_sec_per_km=(
                self._calculate_pace(
                    distance_km=distance_km,
                    duration_sec=duration_sec,
                )
            ),
            records_count=None,
            laps_count=self._to_int(
                activity.get("icu_lap_count")
            ),
            activity_name=activity_name,
            description=description,
            external_type=external_type,
            source_platform=self._to_string(
                activity.get("source")
            ),
            training_load=self._to_float(
                activity.get("icu_training_load")
            ),
            rpe=self._to_float(
                activity.get("icu_rpe")
            ),
            race=race,
            interval_summary=self._serialize_json(
                activity.get("interval_summary")
            ),
            declared_workout_type=(
                declared_classification.workout_type
            ),
            declared_session_role=(
                declared_classification.session_role    
            ),
        )

    def build_source_key(
        self,
        activity_id: str,
    ) -> str:
        return (
            f"{self.SOURCE_PREFIX}:"
            f"{activity_id}"
        )

    def _parse_start_time(
        self,
        value: str | None,
    ) -> datetime:
        if not value:
            raise ValueError(
                "Intervals activity is missing "
                "start_date_local."
            )

        try:
            return datetime.fromisoformat(value)

        except ValueError as exc:
            raise ValueError(
                "Invalid Intervals start_date_local."
            ) from exc

    def _map_sport(
        self,
        intervals_type: str | None,
    ) -> str:
        if not intervals_type:
            return "unknown"

        return self.SPORT_MAPPING.get(
            intervals_type,
            intervals_type.lower(),
        )

    def _meters_to_km(
        self,
        value,
    ) -> float | None:
        numeric = self._to_float(value)

        if numeric is None:
            return None

        return round(
            numeric / 1000,
            3,
        )

    def _get_duration_sec(
        self,
        activity: dict,
    ) -> float | None:
        for field in (
            "moving_time",
            "icu_recording_time",
            "elapsed_time",
        ):
            value = self._to_float(
                activity.get(field)
            )

            if value is not None:
                return value

        return None

    def _calculate_pace(
        self,
        distance_km: float | None,
        duration_sec: float | None,
    ) -> float | None:
        if (
            distance_km is None
            or distance_km <= 0
            or duration_sec is None
            or duration_sec <= 0
        ):
            return None

        return round(
            duration_sec / distance_km,
            2,
        )

    def _serialize_json(
        self,
        value,
    ) -> str | None:
        if value is None:
            return None

        return json.dumps(
            value,
            ensure_ascii=False,
        )

    def _to_string(
        self,
        value,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()

        return normalized or None

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

    def _to_bool(
        self,
        value,
    ) -> bool | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true",
            "1",
            "yes",
        }