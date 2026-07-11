from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.models.workout_intent import WorkoutIntent


@dataclass
class PlannedWorkout:

    planned_date: date

    title: str

    description: str

    workout_type: str

    intent: WorkoutIntent

    planned_distance_km: Optional[float]

    planned_duration_min: Optional[int]

    structure: list[dict]

    priority: str