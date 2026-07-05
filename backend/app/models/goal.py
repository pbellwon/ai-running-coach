from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Goal:

    goal_type: str

    distance_km: Optional[float]

    target_time_sec: Optional[int]

    target_date: Optional[date]

    priority: str = "A"

    notes: str = ""