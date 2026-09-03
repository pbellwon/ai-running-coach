from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class CapabilityTrend:
    area: str

    status: str

    trend: float | None

    confidence: float

    evidence: list[str] = field(
        default_factory=list
    )


@dataclass
class GoalProgress:
    target_date: date

    goal_distance_km: float

    target_time_sec: int

    status: str

    confidence: float

    fitness_trend: str

    goal_gap: str

    primary_limiter: str | None

    secondary_limiter: str | None

    capabilities: list[CapabilityTrend] = field(
        default_factory=list
    )

    evidence: list[str] = field(
        default_factory=list
    )