import re
from datetime import date
from typing import Optional

from app.engine.workout_intent_engine import WorkoutIntentEngine
from app.models.planned_workout import PlannedWorkout
from app.engine.workout_structure_parser import WorkoutStructureParser


class PlannedWorkoutEngine:

    def build(
        self,
        planned_date: date,
        title: str,
        description: str,
        planned_distance_km: Optional[float] = None,
        planned_duration_min: Optional[int] = None,
        priority: str = "normal",
        structure: Optional[list[dict]] = None,
    ) -> PlannedWorkout:

        # Historical descriptions remain visible, but only the latest accepted
        # prescription determines classification and interval structure.
        active_description = description.rsplit("\n\nObowiązujący trening po korekcie PaceMind:\n", 1)[-1]
        # A generated unit also ends in an audit note. Its words (e.g. "startów")
        # must not turn an easy run into strides or a race in the classifier.
        body, separator, note = active_description.rpartition("\nPaceMind ")
        if separator and re.match(r"\d{4}-\d{2}-\d{2} \| Zmiana:", note):
            active_description = body
        classification_text = f"{title} {active_description}".strip()

        # Calendar names and notes can contain words such as "Forest" or
        # "odpoczynek"; a reviewed race entry remains a race regardless of them.
        if title.startswith("Zawody:") and separator and re.match(r"\d{4}-\d{2}-\d{2} \| Zmiana:", note):
            intent = WorkoutIntentEngine().classify("race")
        else:
            intent = WorkoutIntentEngine().classify_from_description(classification_text)

        return PlannedWorkout(
            planned_date=planned_date,
            title=title,
            description=description,
            workout_type=intent.workout_type,
            intent=intent,
            planned_distance_km=planned_distance_km,
            planned_duration_min=planned_duration_min,
            structure=structure or WorkoutStructureParser().parse(active_description),
            priority=priority,
        )

    def build_test_workout(self) -> PlannedWorkout:

        return self.build(
            planned_date=date(2026, 7, 15),
            title="Threshold + fast reps",
            description="3x3km threshold + 4x200",
            planned_distance_km=14.0,
            planned_duration_min=70,
            priority="key",
            structure=[
                {
                    "segment": "warmup",
                    "description": "Easy running",
                    "duration_min": 15,
                },
                {
                    "segment": "main",
                    "description": "3 x 3 km threshold",
                    "repetitions": 3,
                    "distance_km": 3,
                    "intensity": "threshold",
                },
                {
                    "segment": "secondary",
                    "description": "4 x 200 m fast relaxed",
                    "repetitions": 4,
                    "distance_m": 200,
                    "intensity": "vo2max",
                },
                {
                    "segment": "cooldown",
                    "description": "Easy running",
                    "duration_min": 10,
                },
            ],
        )