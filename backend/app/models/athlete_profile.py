from dataclasses import dataclass
from typing import Optional


@dataclass
class AthleteProfile:

    total_workouts: int

    total_distance_km: float

    running_workouts: int

    running_distance_km: float

    running_hours: float

    cross_training_hours: float

    strength_hours: float

    average_weekly_distance_km: float

    longest_run_km: float

    training_sessions_per_week: float
    
    max_hr: int

    threshold_hr: Optional[int]

    threshold_pace: Optional[float]

    easy_pace: Optional[float]