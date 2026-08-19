from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrainingDecision:
    decision: str

    confidence: float

    recovery_status: str
    fatigue_signal: str

    planned_workout_type: str | None
    planned_session_role: str | None

    reasons: list[str]
    warnings: list[str]