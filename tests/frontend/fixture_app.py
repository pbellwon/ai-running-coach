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
    state['clarification_answer_seen'] = False
    state['review_mode'] = 'reduce'
    correction_sheet.__init__()
    race_sheet.__init__()
    with SessionLocal() as db:
        db.query(PlanExecutionReviewDB).delete()
        db.query(ActivePlanStateDB).delete()
        db.query(AthleteProfileProposalDB).delete()
        db.query(AthleteMemoryDetailsDB).delete()
        db.query(AthleteMemoryDB).delete()
        db.query(AthleteProfileStateDB).delete()
        import json
        db.add(AthleteProfileStateDB(id=1,revision=0,
            goal_json=json.dumps({'date':'2026-11-11','name':'10 km','distance_km':10,'priority':'A','target_time':'38:30','notes':''}),
            cycle_json=json.dumps({'cycle_days':10,'anchor_date':None}),updated_at=datetime(2026,11,1)))
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
        import json
        question = json.loads(kwargs['input_text']).get('question','')
        if question == 'Boli mnie Achilles po akcentach.':
            return json.dumps({'answer':'Czy zapamiętać Twoje zgłoszenie?', 'suggestions':[{'category':'injury',
                'text':'Ból Achillesa po akcentach.','fact_status':'current','quote':question,'replace_id':None}]})
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
from app.db.models import RacePlanDraftDB, TrainingPreferencesDB, AthleteProfileProposalDB, AthleteProfileStateDB, AthleteMemoryDB, AthleteMemoryDetailsDB

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
        data=json.loads(kwargs['input_text'])
        followup=data.get('context',{}).get('clarification')
        if followup:
            state['clarification_answer_seen']=bool(followup['questions'] and followup['answer'])
        if 'Potrzebne pytanie testowe' in data.get('athlete_note','') and not followup:
            return json.dumps({'cycle_days':10,'status':'clarify','health':'unclear','start_offset':0,
                'anchor_note':'Początek wymaga potwierdzenia.','explanation':'Doprecyzujmy datę i dolegliwości.',
                'evidence':['history'],'questions':['Czy od 1 grudnia, a ból ustąpił?'],'days':[]})
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

@app.post('/__test__/protect-race-plan')
def protect_race_plan():
    race_sheet.rows = []
    for offset in range(49):
        day = date(2026, 11, 2) + timedelta(days=offset)
        race_day = day == date(2026, 12, 13)
        title = 'Zawody: Start' if race_day else 'Spokojny bieg'
        race_sheet.rows.append({'date': day.isoformat(), 'title': title,
            'description': 'Oryginał\n\nObowiązujący trening po korekcie PaceMind:\n' + title + '\nPaceMind 2026-11-01 | Zmiana: korekta jednostki.',
            'planned_distance_km': '10' if race_day else '6', 'planned_duration_min': '' if race_day else '36',
            'priority':'key' if race_day else 'normal', 'uwagi':'zachowaj'})
    return {'ok': True}

from app.api import athlete_profile
from app.services.athlete_profile_service import AthleteProfileService
app.dependency_overrides[athlete_profile.service] = lambda: AthleteProfileService(source=race_sheet,today=lambda:date(2026,11,1))

@app.post('/__test__/allow-next-planning-attempt')
def next_planning_attempt():
    with SessionLocal() as db:
        db.query(CoachChatGateDB).update({'next_allowed_at':datetime(2000,1,1)})
        db.commit()
    return {'ok':True}

@app.get('/__test__/clarification-answer-seen')
def clarification_answer_seen():
    return {'seen':state.get('clarification_answer_seen',False)}

from app.api import plan_reviews
from app.services.plan_review_service import PlanReviewService
from app.services.plan_review_evidence import PlanReviewEvidence
from app.services.plan_correction_service import digest
from app.db.models import ActivePlanStateDB, PlanExecutionReviewDB
from app.engine.race_plan_engine import parse_calendar

class FixtureReviewAthlete:
    def capture(self,today):
        return {'version':'r'*64,'facts':{'profile':{'goal':parse_calendar(race_sheet.race_calendar_snapshot())[0],'memory':[]}}}

def fixture_review_evidence(*args):
    status='on_target' if state.get('review_mode')=='keep' else 'too_hard'
    return {'days':[{'date':day,'status':'completed','planned_workouts':[{'title':'Threshold','planned_distance_km':10,'planned_duration_min':60}],
        'executed_sessions':[{'workout_type':'threshold','total_distance_km':12,'total_duration_min':70,
            'execution_review':{'status':status,'confidence':.9,'athlete_feedback':{'perceived_effort':9,'comment':'Duże zmęczenie.'}}}]} for day in ('2026-11-02','2026-11-04')],
        'recovery':{'available_days':5,'fatigue_signal':'stable' if status=='on_target' else 'accumulating'},
        'goal_progress':{'fitness_trend':'stable'}}

PlanReviewEvidence.build=lambda self,*args:fixture_review_evidence(*args)
app.dependency_overrides[plan_reviews.service]=lambda:PlanReviewService(source=race_sheet,now=lambda:datetime(2026,11,8,12),athlete_context=FixtureReviewAthlete())

@app.post('/__test__/seed-accepted-review-plan')
def seed_accepted_review_plan():
    import json
    from uuid import uuid4
    root=str(uuid4())
    race_sheet.rows=[{'date':(date(2026,10,26)+timedelta(days=i)).isoformat(),'title':'Threshold','description':'3 x 4 min threshold. Uwagi: zachowaj.',
        'planned_distance_km':'10','planned_duration_min':'60','priority':'normal','uwagi':'notatka'} for i in range(56)]
    snapshot=race_sheet.correction_snapshot()
    goal=parse_calendar(race_sheet.race_calendar_snapshot())[0]
    payload={'id':root,'start':'2026-10-26','end':'2026-12-20','planning_mode':'long-term-10-day-v1',
        'after_snapshot':snapshot,'before_snapshot':snapshot,'calendar_version':digest(race_sheet.race_calendar_snapshot()),
        'long_term':{'goal':goal,'phases':[],'assumptions':[]},'cycles':[{'start':'2026-10-26','end':'2026-11-04','phase':'Rozwój','planned_km':100,'budget_km':100}],
        'coaching':{'status':'ready','explanation':'Plan','anchor_note':'Cykl','evidence':[],'questions':[]},
        'entries':[],'summary':{'added':56,'replaced':0,'kept':0},'created_at':'2026-10-25','warnings':[],'blockers':[],'can_accept':True}
    with SessionLocal() as db:
        db.add(RacePlanDraftDB(id=root,request_hash='root',payload=json.dumps(payload),status='applied',created_at=datetime(2026,10,25)))
        db.commit()
    return {'id':root}

@app.post('/__test__/review-mode/{mode}')
def review_mode(mode:str):
    state['review_mode']=mode
    return {'ok':True}

app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend"))
