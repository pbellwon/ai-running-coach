from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Workout(BaseModel):

    id: str

    date: datetime

    sport: str

    title: str

    duration_seconds: int

    distance_meters: float

    average_hr: Optional[int] = None

    max_hr: Optional[int] = None

    average_pace: Optional[float] = None

    average_cadence: Optional[float] = None

    elevation_gain: Optional[float] = None

    training_load: Optional[float] = None