from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WorkoutFeedback:
    session_id: str

    perceived_effort: float | None

    execution_feeling: str | None

    comment: str | None

    created_at: datetime

    updated_at: datetime
