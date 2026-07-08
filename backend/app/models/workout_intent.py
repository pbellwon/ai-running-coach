from dataclasses import dataclass


@dataclass
class WorkoutIntent:

    workout_type: str

    primary_capability: str

    secondary_capabilities: list[str]

    modifiers: list[str]

    components: list[dict]

    expected_intensity: str

    expected_load: str

    success_metrics: list[str]

    description: str