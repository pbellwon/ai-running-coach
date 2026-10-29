from dataclasses import dataclass
from datetime import datetime
from typing import Literal


AdaptationResponse = Literal[
    "accepted",
    "rejected",
]


@dataclass
class AdaptationDecisionRecord:
    target_date: str

    original_workout_type: str
    proposed_workout_type: str | None

    proposal_decision: str
    athlete_response: AdaptationResponse

    created_at: datetime
    proposal_id: str | None = None
