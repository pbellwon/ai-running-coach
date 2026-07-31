from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExecutedSessionComponent:
    """
    A single recorded activity belonging to a logical training session.
    """

    workout: Any
    workout_file: str
    start_time: datetime
    end_time: datetime
    sport: str
    distance_km: float | None
    duration_min: float | None
    workout_type: str
    confidence: float
    classification_method: str
    warnings: list[str] = field(default_factory=list)
    role: str = "main"


@dataclass
class ExecutedSession:
    """
    A logical training session composed of one or more recorded activities.
    """

    session_id: str
    start_time: datetime
    end_time: datetime
    sport_family: str
    workout_type: str
    confidence: float
    classification_method: str
    components: list[ExecutedSessionComponent]
    total_distance_km: float | None
    total_duration_min: float | None
    warnings: list[str] = field(default_factory=list)

    @property
    def source_file(self) -> str:
        """
        Compatibility key used by WorkoutTypeMatcher.

        For a composite session this is the logical session ID,
        not a physical FIT filename.
        """
        return self.session_id

    @property
    def source_files(self) -> list[str]:
        return [
            component.workout_file
            for component in self.components
        ]

    @property
    def activities_count(self) -> int:
        return len(self.components)

    @property
    def main_component(self) -> ExecutedSessionComponent | None:
        for component in self.components:
            if component.role == "main":
                return component

        return None