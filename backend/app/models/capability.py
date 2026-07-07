from dataclasses import dataclass


@dataclass
class Capability:

    area: str

    score: float

    confidence: float

    evidence: list[str]