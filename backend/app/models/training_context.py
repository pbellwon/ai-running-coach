from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class LastTrainingSession:
    session_id: str
    start_time: datetime
    sport_family: str
    workout_type: str
    distance_km: float | None
    duration_min: float | None
    hours_before_window_end: float


@dataclass
class TrainingContext:
    target_date: date
    window_days: int

    source_activities_count: int
    logical_sessions_count: int

    total_training_min: float
    running_distance_km: float
    running_duration_min: float

    running_sessions: int
    easy_sessions: int
    quality_sessions: int
    long_run_sessions: int
    strength_sessions: int
    cycling_sessions: int
    other_sessions: int

    recent_48h_sessions: int
    recent_48h_training_min: float
    recent_48h_quality_sessions: int
    recent_48h_strength_sessions: int

    type_counts: dict[str, int]

    last_session: LastTrainingSession | None