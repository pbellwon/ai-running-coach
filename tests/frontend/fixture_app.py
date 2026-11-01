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
    state["chat_clock"] = 0
    correction_sheet.__init__()
    race_sheet.__init__()
    with SessionLocal() as db:
        db.query(RacePlanDraftDB).delete()
        db.query(TrainingPreferencesDB).delete()
        db.query(PlanCorrectionDB).delete()
        db.query(PlanWriteGateDB).delete()
        db.query(CoachChatTurnDB).delete()
        db.query(CoachConversationDB).delete()
        db.query(CoachChatGateDB).delete()
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
    from app.services.recent_execution_review_service import RecentExecutionReviewService
    return {"items": RecentExecutionReviewService(
        plan_source=FixturePlanSource(), plan_importer=FixtureImporter(),
        session_builder=CompositeSessionBuilder(resolver=FixtureResolver()),
    ).build(target_date=date(2026, 10, 29), limit=3)}


app.include_router(main.app.router)

# Chat uses real HTTP authentication, SQL persistence and idempotency; only external data/LLM are fixtures.
import os
from app.api import coach_chat
from app.services.coach_chat_service import CoachChatService
from app.db.models import CoachConversationDB, CoachChatTurnDB, CoachChatGateDB
os.environ['COACH_CHAT_ACCESS_CODE'] = 'fixture-private-chat-code'
state['chat_clock'] = 0


class FixtureChatContext:
    def build(self, selection):
        return {'as_of': '2026-10-29T12:00:00Z', 'selection': selection,
                'facts': {'goal': '10 km w 38:30'},
                'sources': [{'label': 'Aktualny cel: 10 km w 38:30'},
                            {'label': 'Wybrany kontekst', **selection}],
                'limitations': ['To interpretacja, nie prognoza wyniku.']}


class FixtureChatLLM:
    def generate(self, **kwargs):
        return 'Ten trening wspiera przygotowania do 10 km. <img src=x onerror=alert(1)> To nie prognoza wyniku.'


def fixture_chat_service():
    state['chat_clock'] += 11
    return CoachChatService(context=FixtureChatContext(), llm=FixtureChatLLM(),
                            now=lambda: datetime(2026, 10, 29, 12) + timedelta(seconds=state['chat_clock']))


main.app.dependency_overrides[coach_chat.service] = fixture_chat_service
app.dependency_overrides[coach_chat.service] = fixture_chat_service

# Corrections exercise real review/decision persistence; only Sheets is an in-memory fixture.
from copy import deepcopy
from app.api import plan_corrections
from app.services.plan_correction_service import PlanCorrectionService
from app.db.models import PlanCorrectionDB, PlanWriteGateDB

class FixtureCorrectionSheet:
    def __init__(self):
        self.rows = [{'date': '2099-11-02', 'title': 'Threshold', 'description': '3 x 10 min. Uwagi: zachowaj. <img src=x onerror=alert(1)>',
                      'planned_distance_km': '10', 'planned_duration_min': '60', 'priority': 'high'}]
    def correction_snapshot(self):
        return {'source': ['fixture', '1'], 'headers': list(self.rows[0]), 'rows': deepcopy(self.rows)}
    def write_correction(self, snapshot, row, before, after):
        self.rows[row - 2] = deepcopy(after)

correction_sheet = FixtureCorrectionSheet()
app.dependency_overrides[plan_corrections.service] = lambda: PlanCorrectionService(source=correction_sheet)


from app.api import race_plans
from app.services.race_plan_service import RacePlanService
from app.db.models import RacePlanDraftDB, TrainingPreferencesDB

class FixtureRaceSheet:
    def __init__(self):
        self.rows = [{'date': '2026-11-03', 'title': 'Threshold', 'description': '3 x 10 min threshold. Uwagi trenera: zachowaj.',
                      'planned_distance_km': '10', 'planned_duration_min': '60', 'priority': 'key', 'uwagi': '=literal'}]
        self.races = [{'date': '2026-12-13', 'name': 'Start <img src=x onerror=alert(1)>', 'distance_km': '10',
                       'priority': 'A', 'target_time': '38:30', 'notes': 'Trasa płaska'}]
        self.writes = 0
    def correction_snapshot(self):
        return {'source': ['fixture-race', '1'], 'headers': list(self.rows[0]), 'rows': deepcopy(self.rows)}
    def race_calendar_snapshot(self):
        return {'source': ['fixture-race', '2'], 'headers': list(self.races[0]), 'rows': deepcopy(self.races)}
    def write_generated_plan(self, before, after):
        self.writes += 1
        self.rows = deepcopy(after['rows'])

race_sheet = FixtureRaceSheet()
from app.services.personal_plan_coach import PersonalPlanCoach

class FixtureAthleteContext:
    def capture(self, today):
        return {'version': 'a'*64, 'facts': {'conversations': ['Ustalono cykl 10-dniowy.'], 'memory': ['Dawna kontuzja, zakończony powrót.']},
                'sources': [{'id': 'history', 'label': 'Historia treningów'}, {'id': 'memory:1', 'label': 'Dawna kontuzja'}],
                'limitations': ['Tylko rozmowy PaceMind'], 'limits': {'cycle_days': 10, 'max_cycle_km': 45, 'max_session_km': 15, 'max_session_minutes': 90, 'history_sufficient': True}}

class FixturePlanModel:
    def generate(self, **kwargs):
        import json
        days = []
        for offset in range(10):
            kind = {0:'easy', 2:'threshold', 4:'easy', 6:'long', 8:'easy'}.get(offset, 'off')
            km = {'easy':6, 'threshold':8, 'long':12, 'off':0}[kind]
            days.append({'offset':offset, 'kind':kind, 'distance_km':km, 'duration_min':km*6,
                         'repetitions':3 if kind=='threshold' else 0, 'work_min':4 if kind=='threshold' else 0,
                         'recovery_min':2 if kind=='threshold' else 0, 'reason':'Odstępy dobrane do reakcji na obciążenie.'})
        if 'Aktualny ból' in json.loads(kwargs['input_text']).get('athlete_note', ''):
            return json.dumps({'cycle_days':10, 'status':'pause', 'health':'active', 'start_offset':0,
                               'anchor_note':'Najpierw doprecyzujmy aktualny ból.', 'explanation':'Nowe zgłoszenie wymaga wyjaśnienia ograniczeń.',
                               'evidence':['history','athlete_note'], 'questions':['Czy ból występuje także podczas chodzenia?'], 'days':[]})
        return json.dumps({'cycle_days':10, 'status':'ready', 'health':'historical', 'start_offset':0,
                           'anchor_note':'Proponuję rozpocząć dzień 1 jutro.', 'explanation':'Historia i dawna kontuzja przemawiają za rozłożeniem bodźców w cyklu 10 dni.',
                           'evidence':['history','memory:1'], 'questions':[], 'days':days})

app.dependency_overrides[race_plans.service] = lambda: RacePlanService(source=race_sheet, now=lambda: datetime(2026, 11, 1, 12),
    athlete_context=FixtureAthleteContext(), coach=PersonalPlanCoach(FixturePlanModel()))

@app.post('/__test__/race-calendar-change')
def change_race_calendar():
    race_sheet.races[0]['target_time'] = '39:00'
    return {'ok': True}

@app.get('/__test__/race-write-count')
def race_write_count():
    return {'count': race_sheet.writes}

app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend"))
