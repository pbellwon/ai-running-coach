from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkoutIntent:

    workout_type: str

    primary_capability: str

    secondary_capability: Optional[str]

    expected_intensity: str

    expected_load: str

    success_metrics: list[str]

    description: str