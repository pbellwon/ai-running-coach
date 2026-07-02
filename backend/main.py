from fastapi import FastAPI
from app.models.athlete import Athlete, AthleteProfile, AthletePhysiology

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Welcome to PaceMind API 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/athlete")
def get_athlete():
    athlete = Athlete(
        id="1",
        profile=AthleteProfile(
            first_name="Paweł",
            age=39,
            height_cm=192,
            weight_kg=77.8
        ),
        physiology=AthletePhysiology(
            vo2max=55
        )
    )

    return athletesource .venv/bin/activate