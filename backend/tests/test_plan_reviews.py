from copy import deepcopy
from datetime import date,datetime,timedelta
from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.db.models import RacePlanDraftDB,ActivePlanStateDB,PlanCorrectionDB,WorkoutDB,DailyAthleteStateDB
from app.engine.plan_adaptation_engine import PlanAdaptationEngine
from app.services.plan_review_service import PlanReviewService
from app.services.plan_review_evidence import PlanReviewEvidence
from app.services.race_plan_service import RacePlanService
from app.services.plan_correction_service import digest
from app.services.coach_errors import ChatError
from app.services.active_plan_service import active_plan
from app.api import plan_reviews
from app.main import app

GOAL={'date':'2027-03-14','name':'Półmaraton','distance_km':21.1,'priority':'A','target_time':'1:27:30','notes':''}
HEADERS=['date','title','description','planned_distance_km','planned_duration_min','priority','notes']


def day_row(day,title='Threshold'):
    return {'date':day,'title':title,'description':'3 x 4 min threshold. Uwagi: zachowaj.','planned_distance_km':'10','planned_duration_min':'60','priority':'normal','notes':'original extra'}


class Source:
    def __init__(self):
        self.plan={'source':['sheet','1'],'headers':HEADERS,'rows':[day_row((date(2026,11,5)+timedelta(days=i)).isoformat()) for i in range(41)]}
        self.calendar={'source':['sheet','2'],'headers':list(GOAL),'rows':[deepcopy(GOAL)]}
        self.writes=0;self.failure=None
    def correction_snapshot(self): return deepcopy(self.plan)
    def race_calendar_snapshot(self): return deepcopy(self.calendar)
    def write_generated_plan(self,before,after):
        self.writes+=1
        if self.failure=='before': raise TimeoutError()
        self.plan=deepcopy(after)
        if self.failure=='after': raise TimeoutError()


class Athlete:
    change=''
    def capture(self,today):
        return {'version':digest(self.change),'facts':{'profile':{'goal':GOAL,'memory':[]}},'sources':[],'limitations':[],'limits':{}}


class Evidence:
    def __init__(self):
        self.value={'days':[{'date':f'2026-11-{i}','status':'completed','planned_workouts':[],
            'executed_sessions':[{'session_id':str(i),'execution_review':{'status':'too_hard','confidence':.9,'athlete_feedback':{'perceived_effort':9}}}]} for i in (12,14)],
            'recovery':{'available_days':5,'fatigue_signal':'accumulating'},'goal_progress':{'fitness_trend':'stable'}}
    def build(self,*args): return deepcopy(self.value)


@pytest.fixture
def setup(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine);factory=sessionmaker(bind=engine)
    source,athlete,evidence=Source(),Athlete(),Evidence()
    root=str(uuid4())
    payload={'id':root,'start':'2026-11-05','end':'2027-03-21','planning_mode':'long-term-10-day-v1',
        'long_term':{'goal':GOAL,'phases':[],'assumptions':[]},'coaching':{'status':'ready','explanation':'pierwotny plan','anchor_note':'cykl','evidence':[],'questions':[]},
        'cycles':[{'start':'2026-11-05','end':'2026-11-14','phase':'Rozwój','budget_km':50,'planned_km':50}],
        'before_snapshot':source.plan,'after_snapshot':source.plan,'calendar_version':digest(source.calendar),
        'created_at':'2026-11-01T12:00:00','summary':{'added':41,'replaced':0,'kept':0},'entries':[],'warnings':[],'blockers':[],'can_accept':True}
    with factory() as db:
        db.add(RacePlanDraftDB(id=root,request_hash='root',payload=json.dumps(payload),status='applied',created_at=datetime(2026,11,1)));db.commit()
    monkeypatch.setattr(PlanReviewEvidence,'build',lambda self,*args:evidence.build(*args))
    svc=PlanReviewService(source,factory,now=lambda:datetime(2026,11,15,12),athlete_context=athlete,evidence=evidence)
    yield svc,source,factory,athlete,evidence,root
    engine.dispose()


def propose(svc,scope='cycle'):
    review=svc.review(str(uuid4()))
    return review,svc.propose(str(uuid4()),review['id'],scope)


def writer(svc): return RacePlanService(svc.source,svc.factory,now=svc.now,athlete_context=svc.athlete)


def test_review_is_readonly_and_uses_accepted_plan(setup):
    svc,source,_,_,_,root=setup
    review=svc.review(str(uuid4()))
    assert review['campaign_id']==review['head_id']==root
    assert review['period_start']=='2026-11-05' and review['period_end']=='2026-11-14'
    assert review['assessment']['decision']=='reduce' and source.writes==0
    assert svc.history()['items'][0]['id']==review['id']


def test_patch_is_same_campaign_changes_only_future_window_and_preserves_notes(setup):
    svc,source,_,_,_,root=setup
    before=deepcopy(source.plan)
    review,patch=propose(svc)
    assert patch['campaign_id']==root and patch['parent_plan_id']==root
    assert patch['planning_mode']=='adaptation-10-day-v1' and source.writes==0
    assert patch['long_term']['goal']==GOAL
    assert patch['campaign_start']=='2026-11-05' and patch['campaign_end']=='2027-03-21'
    for entry in patch['entries']:
        assert '2026-11-16'<=entry['after']['date']<='2026-11-25'
        assert entry['after']['description'].startswith(entry['before']['description'])
        assert entry['after']['notes']=='original extra'
        assert entry['after']['planned_distance_km']=='8'
    saved=writer(svc).decide(patch['id'],True)
    assert saved['status']=='applied' and source.writes==1
    active=active_plan(svc.factory)
    assert active['campaign_id']==root and active['head_id']==patch['id']
    assert source.plan['rows'][:11]==before['rows'][:11]
    # Reviewing the adapted plan still uses original past dates, not the future patch start.
    assert svc.review(str(uuid4()))['period_start']=='2026-11-05'


@pytest.mark.parametrize('mode',['keep','missing','single','pain'])
def test_no_automatic_patch_without_sufficient_support(setup,mode):
    svc,source,_,athlete,evidence,_=setup
    if mode=='keep':
        evidence.value['recovery']['fatigue_signal']='stable'
        for day in evidence.value['days']: day['executed_sessions'][0]['execution_review']['status']='on_target'
    elif mode=='missing': evidence.value['days']=[]
    elif mode=='single': evidence.value['days']=evidence.value['days'][:1]
    else:
        original=athlete.capture
        def capture(today):
            value=original(today);value['facts']['profile']['memory']=[{'category':'injury','status':'current'}];return value
        athlete.capture=capture
    review=svc.review(str(uuid4()))
    assert not review['assessment']['can_propose']
    with pytest.raises(ChatError):svc.propose(str(uuid4()),review['id'],'cycle')
    assert source.writes==0


@pytest.mark.parametrize('what',['sheet','feedback','athlete','calendar','head'])
def test_stale_patch_never_writes(setup,what):
    svc,source,factory,athlete,evidence,_=setup
    _,patch=propose(svc)
    if what=='sheet':source.plan['rows'][12]['notes']='new manual comment'
    elif what=='feedback':evidence.value['days'][0]['executed_sessions'][0]['execution_review']['status']='on_target'
    elif what=='athlete':athlete.change='new injury'
    elif what=='calendar':source.calendar['rows'][0]['target_time']='1:28:00'
    else:
        with factory() as db:db.query(ActivePlanStateDB).update({'campaign_id':'other'});db.commit()
    with pytest.raises(ChatError):writer(svc).decide(patch['id'],True)
    assert source.writes==0


def test_races_single_corrections_and_manual_edits_remain_untouched(setup):
    svc,source,factory,_,_,root=setup
    source.plan['rows'][12]['description']='Original\n\nObowiązujący trening po korekcie PaceMind:\nSpokojny bieg\nPaceMind 2026-11-01 | Zmiana: moja korekta.'
    with factory() as db:
        record=db.get(RacePlanDraftDB,root);value=json.loads(record.payload);value['after_snapshot']=deepcopy(source.plan);record.payload=json.dumps(value);db.commit()
    source.plan['rows'][13]['title']='Manual change'
    _,patch=propose(svc)
    changed={entry['row'] for entry in patch['entries']}
    assert 14 not in changed and 15 not in changed
    assert patch['warnings']


def test_uncertain_write_never_replayed_and_rejection_is_readonly(setup):
    svc,source,_,_,_,_=setup
    _,patch=propose(svc)
    source.failure='after'
    assert writer(svc).decide(patch['id'],True)['status']=='applied'
    assert writer(svc).decide(patch['id'],True)['status']=='applied' and source.writes==1
    _,second=propose(svc)
    assert writer(svc).decide(second['id'],False)['status']=='rejected'
    assert source.writes==1


def test_scope_bounds_and_idempotent_preview(setup):
    svc,_,_,_,_,_=setup
    for scope,maximum in [('unit',1),('cycle',10),('block',30)]:
        review,patch=propose(svc,scope)
        assert 0<len(patch['entries'])<=maximum
        assert svc.propose(patch['id'],review['id'],scope)['id']==patch['id']


def test_review_auth_and_scope_validation(setup,monkeypatch):
    svc,_,_,_,_,_=setup
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE','private-review-owner-code')
    app.dependency_overrides[plan_reviews.service]=lambda:svc
    client=TestClient(app);headers={'Authorization':'Bearer private-review-owner-code'}
    try:
        assert client.get('/coach/plan-reviews/current').status_code==401
        assert client.get('/coach/plan-reviews/current',headers=headers).status_code==200
        response=client.post('/coach/plan-reviews',headers=headers,json={'id':str(uuid4())})
        assert response.status_code==200
        assert client.post('/coach/plan-reviews/proposals',headers=headers,json={'id':str(uuid4()),'review_id':response.json()['id'],'scope':'year'}).status_code==422
    finally:app.dependency_overrides.pop(plan_reviews.service)


def test_review_applies_approved_single_workout_correction_to_historical_baseline(setup):
    svc,source,factory,_,evidence,_=setup
    old=deepcopy(source.plan['rows'][7]);changed=dict(old,planned_distance_km='8',title='Spokojny bieg')
    source.plan['rows'][7]=changed
    with factory() as db:
        db.add(PlanCorrectionDB(id=str(uuid4()),request_hash='one',status='applied',created_at=datetime(2026,11,12),
            payload=json.dumps({'row':9,'source':source.plan['source'],'before':old,'after':changed})))
        db.commit()
    original=evidence.build
    captured=[]
    def build(snapshot,*args):
        captured.append(deepcopy(snapshot));return original(snapshot,*args)
    evidence.build=build
    svc.review(str(uuid4()))
    assert captured[0]['rows'][7]['planned_distance_km']=='8'


def test_real_execution_feedback_recovery_and_trend_services_share_the_ten_day_window():
    from app.db.models import AthleteProfileStateDB,WorkoutFeedbackDB
    from app.services.composite_session_builder import CompositeSessionBuilder
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine);factory=sessionmaker(bind=engine)
    try:
        with factory() as db:
            db.add(AthleteProfileStateDB(id=1,revision=0,goal_json=json.dumps(GOAL),cycle_json='{"cycle_days":10,"anchor_date":null}',updated_at=datetime(2026,11,1)))
            for source_file,start,km,seconds,kind in [('wu.fit',datetime(2026,11,7,8),2,600,'easy_run'),('main.fit',datetime(2026,11,7,8,20),8,3000,'threshold'),('next.fit',datetime(2026,11,10,8),10,3600,'threshold')]:
                db.add(WorkoutDB(source_file=source_file,start_time=start,sport='running',distance_km=km,duration_sec=seconds,declared_workout_type=kind))
            for offset in range(26):
                db.add(DailyAthleteStateDB(date=datetime(2026,10,20)+timedelta(days=offset),hrv=60,resting_hr=50,sleep_sec=8*3600,sleep_score=85))
            db.commit()
            sessions=CompositeSessionBuilder().build(db.query(WorkoutDB).all())
            db.add(WorkoutFeedbackDB(session_id=sessions[0].session_id,perceived_effort=8,comment='Mocniej niż zwykle',created_at=datetime(2026,11,7),updated_at=datetime(2026,11,7)))
            db.commit()
        evidence=PlanReviewEvidence(factory).build(Source().plan,date(2026,11,5),date(2026,11,14),date(2026,11,15))
        assert len(evidence['days'])==10
        sessions=[s for d in evidence['days'] for s in d['executed_sessions']]
        assert len(sessions)==2
        assert sum(s['activities_count'] for s in sessions)==3
        assert any(s['execution_review']['athlete_feedback'] for s in sessions)
        assert evidence['recovery']['available_days']==10
        assert evidence['current_recovery']['available_days']==5
        assert evidence['goal_progress']['goal_distance_km']==21.1
    finally:engine.dispose()
