from dataclasses import dataclass


@dataclass
class CurrentFitness:

    period_weeks: int

    running_distance_km: float

    running_hours: float

    running_sessions: int

    running_sessions_per_week: float

    average_weekly_distance_km: float

    cross_training_hours: float

    strength_hours: float

    longest_run_km: float

    consistency: float