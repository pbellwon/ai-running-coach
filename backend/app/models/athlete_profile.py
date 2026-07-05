from dataclasses import dataclass
from typing import Optional


@dataclass
class AthleteProfile:

    total_workouts: int

    total_distance_km: float

    average_weekly_distance_km: float

    longest_run_km: float

    average_long_run_km: float

    training_days_per_week: float

    max_hr: int

    threshold_hr: Optional[int]

    threshold_pace: Optional[float]

    easy_pace: Optional[float]