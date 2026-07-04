from pydantic import BaseModel
from datetime import date


class Workout(BaseModel):
    date: date
    sport: str
    title: str

    duration_seconds: int
    distance_meters: float

    avg_hr: int
    max_hr: int
    avg_pace: float

    def duration_minutes(self) -> float:
        return self.duration_seconds / 60

    def distance_km(self) -> float:
        return self.distance_meters / 1000