from __future__ import annotations

from datetime import datetime

from app.db.models import WorkoutDB


class IntervalsActivityMapper:
    """
    Maps an Intervals.icu activity payload into the current
    PaceMind WorkoutDB model.

    The mapper intentionally uses only stable fields required
    by the existing domain model.

    Intervals-specific metadata such as training load, RPE,
    CTL and ATL will be added in a later schema extension.
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

    def map(self, activity: dict) -> WorkoutDB:
        activity_id = activity.get("id")

        if not activity_id:
            raise ValueError(
                "Intervals activity is missing id."
            )

        start_time = self._parse_start_time(
            activity.get("start_date_local")
        )

        sport = self._map_sport(
            activity.get("type")
        )

        distance_km = self._meters_to_km(
            activity.get("distance")
        )

        duration_sec = self._get_duration_sec(
            activity
        )

        avg_hr = self._to_float(
            activity.get("average_heartrate")
        )

        max_hr = self._to_float(
            activity.get("max_heartrate")
        )

        avg_pace_sec_per_km = (
            self._calculate_pace(
                distance_km=distance_km,
                duration_sec=duration_sec,
            )
        )

        laps_count = self._to_int(
            activity.get("icu_lap_count")
        )

        return WorkoutDB(
            source_file=self.build_source_key(
                activity_id
            ),
            start_time=start_time,
            sport=sport,
            distance_km=distance_km,
            duration_sec=duration_sec,
            avg_hr=avg_hr,
            max_hr=max_hr,
            avg_pace_sec_per_km=(
                avg_pace_sec_per_km
            ),
            records_count=None,
            laps_count=laps_count,
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
            return datetime.fromisoformat(
                value
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid Intervals "
                "start_date_local."
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
        """
        Prefer moving_time for endurance activities.

        Fall back to recording_time and finally elapsed_time.
        """

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