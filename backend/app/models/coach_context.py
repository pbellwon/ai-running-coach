from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CoachContext:
    """
    Structured context passed to AI-facing PaceMind services.

    This model contains already-computed PaceMind facts.
    The LLM should interpret this context, not recreate
    deterministic training logic.
    """

    schema_version: str

    target_date: str

    goal: dict[str, Any]

    today: dict[str, Any]

    goal_progress: dict[str, Any]

    athlete_memory: list[
        dict[str, Any]
    ]