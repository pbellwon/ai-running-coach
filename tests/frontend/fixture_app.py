"""Local browser fixture: real decision API/SQLite, deterministic training inputs."""
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import main
from app.db.database import SessionLocal
from app.db.models import AdaptationDecisionRecordDB, WorkoutDB, DailyAthleteStateDB
from app.models.adaptation_proposal import AdaptationProposal
from app.models.planned_workout import PlannedWorkout
from app.services.weekly_coach_review_service import WeeklyCoachReviewService
from app.services.weekly_review_service import WeeklyReviewService
from app.services.composite_session_builder import CompositeSessionBuilder


def make_proposal():
    return AdaptationProposal(
        target_date=date(2026, 10, 29),
        original_workout_title="Threshold 3 x 10 min",
        original_workout_type="threshold",
        decision="reduce_load",
        proposed_workout_type="threshold",
        proposed_distance_km=8.0,
        proposed_duration_min=45,
        reason="Recent fatigue",
        warnings=["Review recovery before training."],
    )


state = {"proposal": make_proposal(), "weekly_mode": "normal"}


class FixturePlanSource:
    def fetch_rows(self):
        if state["weekly_mode"] == "failure":
            raise RuntimeError("Fixture plan source unavailable")
        if state["weekly_mode"] == "empty":
            return []
        return [
            PlannedWorkout(
                planned_date=date(2026, 10, day), title=title, description=title,
                workout_type=kind, intent=None, planned_distance_km=distance,
                planned_duration_min=duration, structure=[], priority="normal",
            )
            for day, kind, title, distance, duration in [
                (19, "easy_run", "Easy <img src=x onerror=alert(1)>", 8, 45),
                (21, "threshold", "Threshold", 5, 30),
                (23, "threshold", "Threshold", 5, 30),
                (26, "easy_run", "Easy", 8, 45),
                (28, "easy_run", "Easy", 8, 45),
                (30, "threshold", "Friday threshold", 5, 30),
                (31, "off", "Rest", None, None),
            ]
        ]


class FixtureImporter:
    def import_rows(self, rows):
        return rows


class FixtureResolver:
    def resolve(self, workout):
        return {"workout_type": workout.declared_workout_type, "confidence": 0.9,
                "classification_method": "fixture", "warnings": []}


def weekly_service():
    return WeeklyCoachReviewService(
        weekly_service=WeeklyReviewService(
            plan_source=FixturePlanSource(), plan_importer=FixtureImporter(),
            session_builder=CompositeSessionBuilder(resolver=FixtureResolver()),
        ),
        today=lambda: date(2026, 10, 29),
    )


class FixturePlanningService:
    def build(self, target_date):
        return state["proposal"]


main.AdaptivePlanningService = FixturePlanningService
main.WeeklyCoachReviewService = weekly_service
app = FastAPI()


@app.post("/__test__/reset")
def reset():
    state["proposal"] = make_proposal()
    state["weekly_mode"] = "normal"
    with SessionLocal() as db:
        db.query(AdaptationDecisionRecordDB).delete()
        db.query(WorkoutDB).delete()
        db.query(DailyAthleteStateDB).delete()
        for day, kind in [(19, "easy_run"), (21, "threshold"), (23, "threshold"), (26, "easy_run")]:
            db.add(WorkoutDB(
                source_file=f"weekly-{day}.fit", start_time=datetime(2026, 10, day, 8),
                sport="running", duration_sec=45 * 60, distance_km=8,
                declared_workout_type=kind,
            ))
        for offset in range(29):
            current = date(2026, 10, 1) + timedelta(days=offset)
            poor = 21 <= current.day <= 25
            db.add(DailyAthleteStateDB(
                date=datetime.combine(current, datetime.min.time()),
                hrv=25 if poor else 60, resting_hr=65 if poor else 48,
                sleep_sec=4 * 3600 if poor else 8 * 3600,
                sleep_score=40 if poor else 85, ctl=40, atl=65 if poor else 40,
            ))
        db.commit()
    return {"ok": True}


@app.post("/__test__/weekly-mode/{mode}")
def set_weekly_mode(mode: str):
    state["weekly_mode"] = mode
    if mode == "empty":
        with SessionLocal() as db:
            db.query(WorkoutDB).delete()
            db.query(DailyAthleteStateDB).delete()
            db.commit()
    return {"ok": True}


@app.post("/__test__/change-proposal")
def change_proposal():
    state["proposal"] = replace(state["proposal"], proposed_distance_km=6.0)
    return {"ok": True}


@app.get("/today")
def today():
    return {
        "target_date": "2026-10-29",
        "status": "ready",
        "planned_workout": {"title": "Threshold", "workout_type": "threshold"},
        "decision": {"decision": "reduce"},
        "recommendation": {
            "title": "Reduce load", "summary": "Recent fatigue", "reasons": [], "warnings": [],
        },
    }


@app.get("/training/overview")
def overview():
    return {}


@app.get("/workouts/recent-reviews")
def recent_reviews():
    return {"items": []}


app.include_router(main.app.router)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend"))
