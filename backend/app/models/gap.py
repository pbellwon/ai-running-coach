from dataclasses import dataclass


@dataclass
class Gap:

    area: str

    current_score: float

    target_score: float

    reason: str

    @property
    def gap(self):
        return round(self.target_score - self.current_score, 1)