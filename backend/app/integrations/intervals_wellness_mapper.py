from __future__ import annotations

from datetime import date

from app.models.daily_athlete_state import (
    DailyAthleteState,
)


class IntervalsWellnessMapper:
    def map(
        self,
        wellness: dict,
    ) -> DailyAthleteState:
        wellness_date = self._parse_date(
            wellness.get("id")
        )

        return DailyAthleteState(
            date=wellness_date,

            resting_hr=self._to_float(
                wellness.get("restingHR")
            ),
            hrv=self._to_float(
                wellness.get("hrv")
            ),
            hrv_sdnn=self._to_float(
                wellness.get("hrvSDNN")
            ),

            sleep_sec=self._to_float(
                wellness.get("sleepSecs")
            ),
            sleep_score=self._to_float(
                wellness.get("sleepScore")
            ),
            sleep_quality=self._to_float(
                wellness.get("sleepQuality")
            ),
            avg_sleeping_hr=self._to_float(
                wellness.get("avgSleepingHR")
            ),

            ctl=self._to_float(
                wellness.get("ctl")
            ),
            atl=self._to_float(
                wellness.get("atl")
            ),
            ramp_rate=self._to_float(
                wellness.get("rampRate")
            ),

            weight_kg=self._to_float(
                wellness.get("weight")
            ),
            vo2max=self._to_float(
                wellness.get("vo2max")
            ),
            steps=self._to_int(
                wellness.get("steps")
            ),

            soreness=self._to_float(
                wellness.get("soreness")
            ),
            fatigue=self._to_float(
                wellness.get("fatigue")
            ),
            stress=self._to_float(
                wellness.get("stress")
            ),
            mood=self._to_float(
                wellness.get("mood")
            ),
            motivation=self._to_float(
                wellness.get("motivation")
            ),
            readiness=self._to_float(
                wellness.get("readiness")
            ),

            spo2=self._to_float(
                wellness.get("spO2")
            ),
        )

    def _parse_date(
        self,
        value: str | None,
    ) -> date:
        if not value:
            raise ValueError(
                "Wellness record is missing id/date."
            )

        try:
            return date.fromisoformat(value)

        except ValueError as exc:
            raise ValueError(
                "Invalid wellness date."
            ) from exc

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