"""Local browser fixture: real decision API/SQLite, deterministic training inputs."""
from dataclasses import replace
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import main
from app.db.database import SessionLocal
from app.db.models import AdaptationDecisionRecordDB
from app.models.adaptation_proposal import AdaptationProposal


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


state = {"proposal": make_proposal()}


class FixturePlanningService:
    def build(self, target_date):
        return state["proposal"]


main.AdaptivePlanningService = FixturePlanningService
app = FastAPI()


@app.post("/__test__/reset")
def reset():
    state["proposal"] = make_proposal()
    with SessionLocal() as db:
        db.query(AdaptationDecisionRecordDB).delete()
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
