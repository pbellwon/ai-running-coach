from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class MetricTrend:
    values: list[float | None]
    direction: str
    valid_samples: int


@dataclass
class RecoveryTrend:
    target_date: date
    window_days: int
    available_days: int

    hrv: MetricTrend
    resting_hr: MetricTrend
    sleep_duration: MetricTrend
    sleep_score: MetricTrend

    caution_days: int
    poor_days: int

    fatigue_signal: str
    fatigue_score: int

    reasons: list[str]