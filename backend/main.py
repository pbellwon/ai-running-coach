from fastapi import FastAPI

app = FastAPI(
    title="PaceMind API",
    description="AI Running Coach API",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to PaceMind API 🚀"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }

from app.models.athlete import Athlete


@app.get("/athlete")
def get_athlete():

    athlete = Athlete(
        id="1",
        first_name="Paweł",
        age=39,
        height_cm=192,
        weight_kg=77.8,
        vo2max=55
    )

    return athlete