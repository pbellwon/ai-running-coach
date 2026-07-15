from dataclasses import dataclass


@dataclass
class WorkoutExecutionComparison:

    planned_workout_type: str

    executed_workout_type: str

    intent_match: bool

    planned_distance_km: float | None

    executed_distance_km: float | None

    distance_match: str

    structure_match: str

    execution_quality: str

    confidence: float

    classification_method: str

    warnings: list[str]