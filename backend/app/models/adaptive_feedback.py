from dataclasses import dataclass


@dataclass
class AdaptiveFeedback:

    decision: str

    risk_level: str

    reason: str

    next_action: str

    confidence: float

    warnings: list[str]