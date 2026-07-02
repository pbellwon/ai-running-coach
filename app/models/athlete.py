from pydantic import BaseModel
from typing import Optional


class Athlete(BaseModel):
    id: str

    first_name: str

    age: int

    height_cm: float

    weight_kg: float

    vo2max: Optional[float] = None

    resting_hr: Optional[int] = None

    max_hr: Optional[int] = None