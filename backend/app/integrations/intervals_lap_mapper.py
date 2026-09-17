from __future__ import annotations

from app.db.models import LapDB


class IntervalsLapMapper:
    """
    Maps Intervals.icu detected intervals into LapDB rows.

    The caller owns persistence and decides whether existing
    rows should be replaced or updated.
    """

    def map(
        self,
        *,
        workout_file: str,
        intervals: list[dict],
    ) -> list[LapDB]:
        if not workout_file:
            raise ValueError(
                "workout_file must not be empty."
            )

        laps: list[LapDB] = []

        lap_number = 0

        for interval in intervals:
            mapped = self._map_interval(
                workout_file=workout_file,
                interval=interval,
                lap_number=lap_number + 1,
            )

            if mapped is None:
                continue

            lap_number += 1

            mapped.lap_number = (
                lap_number
            )

            laps.append(
                mapped
            )

        return laps

    def _map_interval(
        self,
        *,
        workout_file: str,
        interval: dict,
        lap_number: int,
    ) -> LapDB | None:
        distance_m = self._as_float(
            interval.get(
                "distance"
            )
        )

        elapsed_time_sec = (
            self._as_float(
                interval.get(
                    "elapsed_time"
                )
            )
        )

        if (
            distance_m is None
            or elapsed_time_sec is None
            or distance_m <= 0
            or elapsed_time_sec <= 0
        ):
            return None

        return LapDB(
            workout_file=workout_file,
            lap_number=lap_number,
            distance_m=distance_m,
            elapsed_time_sec=elapsed_time_sec,
            avg_hr=self._as_float(
                interval.get(
                    "average_heartrate"
                )
            ),
            max_hr=self._as_float(
                interval.get(
                    "max_heartrate"
                )
            ),
        )

    def _as_float(
        self,
        value,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None