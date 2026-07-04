from fastapi import FastAPI
from app.models.athlete import Athlete, AthleteProfile, AthletePhysiology
from app.db.database import Base, engine
from app.db import models
from app.services.fit_importer import FITImporter

app = FastAPI()

Base.metadata.create_all(bind=engine)


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

    return athlete

from app.services.csv_importer import CSVWorkoutImporter


@app.get("/workouts/raw")
def get_raw_workouts():

    importer = CSVWorkoutImporter(
        "data/imports/workouts_sample.csv"
    )

    return importer.load_workouts()

from app.engine.training_metrics import TrainingMetricsEngine
from app.services.csv_importer import CSVWorkoutImporter


@app.get("/workouts/analyzed")
def analyze_workouts():

    importer = CSVWorkoutImporter("data/imports/workouts_sample.csv")
    workouts = importer.load_workouts()

    engine = TrainingMetricsEngine()

    return [
        engine.analyze(w)
        for w in workouts
    ]

from app.engine.training_metrics import TrainingMetricsEngine
from app.engine.coach_engine import CoachEngine
from app.services.csv_importer import CSVWorkoutImporter


@app.get("/coach/summary")
def coach_summary():

    importer = CSVWorkoutImporter("data/imports/workouts_sample.csv")
    workouts = importer.load_workouts()

    metrics_engine = TrainingMetricsEngine()
    coach_engine = CoachEngine()

    results = []

    for w in workouts:
        metrics = metrics_engine.analyze(w)
        decision = coach_engine.make_recommendation(metrics)

        results.append({
            "workout": metrics,
            "coach": decision
        })

    return results


from pathlib import Path
from fitparse import FitFile
import gzip


@app.get("/fit/test")
def test_fit():

    folder = Path("data/imports/trainingpeaks_fit")

    file = next(folder.glob("*.FIT.gz"))

    with gzip.open(file, "rb") as gz:
        fit = FitFile(gz)

        messages = list(fit.get_messages("session"))

    return {
        "file": file.name,
        "sessions": len(messages)
    }


@app.get("/fit/decode-one")
def decode_one_fit():
    importer = FITImporter("data/imports/trainingpeaks_fit")
    return importer.decode_one_file()