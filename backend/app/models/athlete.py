from pydantic import BaseModel


class AthleteProfile(BaseModel):
    first_name: str
    age: int
    height_cm: float
    weight_kg: float


class AthletePhysiology(BaseModel):
    vo2max: float


class Athlete(BaseModel):
    id: str
    profile: AthleteProfile
    physiology: AthletePhysiology