from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class RecoveryMetric:
    current: float | None
    baseline: float | None
    difference: float | None
    difference_percent: float | None
    status: str
    sample_size: int


@dataclass
class RecoverySnapshot:
    date: date

    hrv: RecoveryMetric
    resting_hr: RecoveryMetric
    sleep_duration: RecoveryMetric
    sleep_score: RecoveryMetric

    ctl: float | None
    atl: float | None
    form: float | None

    overall_status: str
    warning_count: int
    available_metrics_count: int
    reasons: list[str]