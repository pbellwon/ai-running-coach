from fastapi import FastAPI
from app.models.athlete import Athlete, AthleteProfile, AthletePhysiology
from app.db.database import Base, engine
from app.db import models
from app.services.fit_importer import FITImporter
from app.analysis.statistics_engine import StatisticsEngine
from app.analysis.training_load_engine import TrainingLoadEngine
from app.analysis.efficiency_analyzer import EfficiencyAnalyzer
from app.analysis.cardiac_drift_analyzer import CardiacDriftAnalyzer
from app.analysis.pace_stability_analyzer import PaceStabilityAnalyzer
from app.analysis.cadence_analyzer import CadenceAnalyzer
from datetime import date
from app.models.goal import Goal
from app.engine.goal_engine import GoalEngine
from app.engine.athlete_gap_analyzer import AthleteGapAnalyzer
from app.engine.goal_feasibility import GoalFeasibility


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

@app.get("/stats/overview")
def stats_overview():
    engine = StatisticsEngine()
    return engine.overview()

@app.get("/stats/training-load-overview")
def training_load_overview():
    engine = StatisticsEngine()
    return engine.training_load_overview()

@app.get("/stats/weekly")
def weekly_stats():
    engine = StatisticsEngine()
    return engine.weekly_overview()

@app.get("/load/workout")
def workout_load(workout_file: str):
    engine = TrainingLoadEngine()
    return engine.analyze_workout(workout_file)

@app.get("/analysis/efficiency")
def efficiency_analysis(workout_file: str):
    analyzer = EfficiencyAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/debug/record")
def debug_record(workout_file: str):
    from app.db.database import SessionLocal
    from app.db.models import RecordDB

    db = SessionLocal()

    record = (
        db.query(RecordDB)
        .filter(RecordDB.workout_file == workout_file)
        .first()
    )

    db.close()

    return record.__dict__ if record else {"error": "not found"}

@app.get("/debug/fit-record")
def debug_fit_record(workout_file: str):
    from pathlib import Path
    from app.services.fit_importer import FITImporter

    importer = FITImporter("data/imports/trainingpeaks_fit")
    file = Path("data/imports/trainingpeaks_fit") / workout_file

    decoded = importer.decode_file(file)

    return decoded["first_record"]

@app.get("/debug/fit-records")
def debug_fit_records(workout_file: str):
    from pathlib import Path
    from app.services.fit_importer import FITImporter

    importer = FITImporter("data/imports/trainingpeaks_fit")
    file = Path("data/imports/trainingpeaks_fit") / workout_file

    decoded = importer.decode_file(file)

    return decoded["records"][:10]

@app.get("/analysis/cardiac-drift")
def cardiac_drift(workout_file: str):
    analyzer = CardiacDriftAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/analysis/pace-stability")
def pace_stability(workout_file: str):
    analyzer = PaceStabilityAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/analysis/cadence")
def cadence_analysis(workout_file: str):
    analyzer = CadenceAnalyzer()
    return analyzer.analyze(workout_file)

@app.get("/goal/test")
def goal_test():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,  # 38:40
        target_date=date(2026, 10, 1),
        priority="A",
        notes="Break 39 minutes for 10K and target around 38:40.",
    )

    engine = GoalEngine()

    return engine.evaluate(goal)

@app.get("/goal/gap-test")
def goal_gap_test():

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,
        target_date=date(2026, 10, 1),
        priority="A",
    )

    athlete = {
        "weekly_distance_km": 42,
        "long_run_km": 14,
        "threshold_pace": None,
        "easy_pace": 5.15,
    }

    analyzer = AthleteGapAnalyzer()

    return analyzer.analyze(goal, athlete)

@app.get("/goal/feasibility")
def goal_feasibility():

    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2320,
        target_date=date(2026, 10, 1),
        priority="A",
    )

    engine = GoalEngine()
    summary = engine.evaluate(goal)

    feasibility = GoalFeasibility()

    return feasibility.evaluate(summary)