from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class DailyAthleteState:
    date: date

    resting_hr: float | None = None
    hrv: float | None = None
    hrv_sdnn: float | None = None

    sleep_sec: float | None = None
    sleep_score: float | None = None
    sleep_quality: float | None = None
    avg_sleeping_hr: float | None = None

    ctl: float | None = None
    atl: float | None = None
    ramp_rate: float | None = None

    weight_kg: float | None = None
    vo2max: float | None = None
    steps: int | None = None

    soreness: float | None = None
    fatigue: float | None = None
    stress: float | None = None
    mood: float | None = None
    motivation: float | None = None
    readiness: float | None = None

    spo2: float | None = None