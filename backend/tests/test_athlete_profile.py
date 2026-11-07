from copy import deepcopy
from datetime import date, datetime
import json
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import AthleteMemoryDB, AthleteProfileProposalDB, CoachChatTurnDB, CoachConversationDB, AthleteProfileStateDB
from app.services.athlete_profile_service import AthleteProfileService
from app.services.athlete_memory_service import AthleteMemoryService
from app.services.current_goal_service import CurrentGoalService
from app.services.personal_plan_context import PersonalPlanContext
from app.services.coach_chat_service import CoachChatService
from app.services.coach_errors import ChatError
from app.api import athlete_profile
from app.main import app


class Calendar:
    def __init__(self):
        self.rows = [{'date':'2027-03-21','name':'Start główny <img src=x>','distance_km':'10','priority':'A','target_time':'38:30','notes':'Trasa płaska'},
                     {'date':'2027-02-21','name':'Kontrola','distance_km':'5','priority':'B','target_time':'','notes':''}]
        self.calls = 0
    def race_calendar_snapshot(self):
        self.calls += 1
        return {'source':['sheet','2'], 'headers':list(self.rows[0]), 'rows':deepcopy(self.rows)}


@pytest.fixture
def profile():
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    source = Calendar()
    svc = AthleteProfileService(factory, source, today=lambda:date(2026,11,7))
    svc.ensure()
    yield svc, factory, source
    engine.dispose()


def memory(**kwargs):
    return dict(kind='memory', category='injury', text='Ból Achillesa po akcentach.', fact_status='current', observed_on='2026-11-07', replace_id=None) | kwargs


def propose(svc, change, **kwargs):
    return svc.propose(str(uuid4()),svc.snapshot()['version'],change,**kwargs)


def goal_change(svc):
    calendar = svc.calendar()
    return {'kind':'goal','calendar_version':calendar['version'],'race_key':calendar['items'][0]['key']}


def test_goal_is_shared_only_after_confirmation_and_not_hardcoded(profile):
    svc,factory,_ = profile
    reader = CurrentGoalService(factory)
    assert reader.get().goal_type == 'unconfigured'
    item = propose(svc,goal_change(svc))
    assert reader.get().target_date is None
    svc.decide(item['id'],True)
    goal = CurrentGoalService(factory).get()
    assert goal.target_date == date(2027,3,21) and goal.target_time_sec == 2310
    assert goal.distance_km == 10
    personal = PersonalPlanContext(factory).capture(date(2026,11,7))
    assert personal['facts']['profile']['goal']['date'] == '2027-03-21'


def test_calendar_edit_blocks_old_goal_and_repeated_saved_request_is_idempotent(profile):
    svc,factory,source = profile
    change = goal_change(svc)
    identifier, version = str(uuid4()), svc.snapshot()['version']
    item = svc.propose(identifier,version,change)
    source.rows[0]['target_time'] = '39:00'
    with pytest.raises(ChatError): svc.decide(item['id'],True)
    assert CurrentGoalService(factory).get().target_time_sec is None
    fresh = propose(svc,goal_change(svc))
    svc.decide(fresh['id'],True)
    before = source.calls
    assert svc.propose(fresh['id'],fresh['base_version'],{k:v for k,v in fresh['change'].items() if k!='race'})['status']=='applied'
    assert source.calls == before


def test_memory_revision_keeps_original_and_resolved_status_is_shared(profile):
    svc,factory,_ = profile
    first = propose(svc,memory())
    assert svc.snapshot()['memory'] == []
    applied = svc.decide(first['id'],True)
    old_id = applied['result']['memory_id']
    second = propose(svc,memory(text='Dawny ból ustąpił.',fact_status='resolved',replace_id=old_id))
    svc.decide(second['id'],True)
    snapshot = svc.snapshot(True)
    assert snapshot['memory'][0]['status']=='resolved'
    assert snapshot['memory'][0]['supersedes_id']==old_id
    assert snapshot['memory_history'][0]['text']=='Ból Achillesa po akcentach.'
    assert snapshot['memory_history'][0]['active'] is False
    assert AthleteMemoryService(factory).list_active()[0].status=='resolved'
    context = PersonalPlanContext(factory).capture(date(2026,11,7))
    assert context['facts']['memory'][0]['status']=='resolved'


def test_concurrent_stale_proposal_cannot_replace_new_knowledge(profile):
    svc,_,_ = profile
    first,second=propose(svc,memory()),propose(svc,memory(text='Inne zgłoszenie'))
    svc.decide(first['id'],True)
    with pytest.raises(ChatError): svc.decide(second['id'],True)
    assert len(svc.snapshot()['memory'])==1


def test_rejection_does_not_change_profile_or_invalidate_other_proposals(profile):
    svc,_,_ = profile
    first,second=propose(svc,memory()),propose(svc,memory(text='Inne zgłoszenie'))
    before=svc.snapshot()['version']
    assert svc.decide(first['id'],False)['status']=='rejected'
    assert svc.snapshot()['version']==before
    svc.decide(second['id'],True)
    with pytest.raises(ChatError): svc.decide(first['id'],True)
    assert svc.decide(second['id'],True)['status']=='applied'


def test_cycle_has_date_based_ten_day_position(profile):
    svc,_,_ = profile
    item=propose(svc,{'kind':'cycle','cycle_days':10,'anchor_date':'2026-11-01'})
    svc.decide(item['id'],True)
    assert svc.snapshot()['cycle_day']==7
    assert svc.snapshot()['cycle']['cycle_days']==10


def test_existing_memory_is_unreviewed_and_not_silently_assumed_current(profile):
    svc,factory,_=profile
    AthleteMemoryService(factory).create('injury','Dawna kontuzja','athlete',.8)
    assert svc.snapshot()['memory'][0]['status']=='unreviewed'


def test_ai_proposal_requires_quote_from_athlete_and_explicit_acceptance(profile):
    svc,factory,_=profile
    class Context:
        def build(self,selection):
            return {'facts':{'athlete_profile':svc.snapshot()},'sources':[{'label':'Profil'}], 'limitations':[], 'as_of':'2026-11-07','selection':selection}
    class Model:
        def generate(self,**kwargs):
            return json.dumps({'answer':'Czy zapamiętać Twoje zgłoszenie?', 'suggestions':[{'category':'injury','text':'Ból po akcentach',
                'fact_status':'current','quote':'Boli mnie Achilles po akcentach.','replace_id':None}]})
    chat=CoachChatService(factory,Context(),Model(),lambda:datetime(2026,11,7,12))
    conversation,request=str(uuid4()),str(uuid4())
    chat.create(conversation)
    reply=chat.send(conversation,request,'Boli mnie Achilles po akcentach.',{'kind':'today'})
    assert len(reply['memory_proposals'])==1 and not svc.snapshot()['memory']
    assert chat.send(conversation,request,'Boli mnie Achilles po akcentach.',{'kind':'today'})==reply
    candidate=reply['memory_proposals'][0]
    svc.decide(candidate['id'],True)
    stored=svc.snapshot()['memory'][0]
    assert stored['source_turn_id']==request and stored['source_quote']=='Boli mnie Achilles po akcentach.'
    assert chat.history(conversation)['turns'][0]['memory_proposals'][0]['status']=='applied'


def test_assistant_text_is_not_a_valid_athlete_source(profile):
    svc,factory,_=profile
    identifier=str(uuid4())
    with factory() as db:
        db.add(CoachConversationDB(id='conversation',title='test',created_at=datetime(2026,11,1),updated_at=datetime(2026,11,1)))
        db.add(CoachChatTurnDB(id=identifier,conversation_id='conversation',message='Co trenować?',answer='Masz kontuzję.',status='completed',request_hash='h',lease='',context_json='{}',evidence_json='{}',created_at=datetime(2026,11,1),updated_at=datetime(2026,11,1)))
        db.commit()
    with pytest.raises(ChatError): propose(svc,memory(),source_turn_id=identifier,quote='Masz kontuzję.')
    assert not svc.snapshot()['memory']


def test_profile_api_auth_validation_and_full_confirmation(profile,monkeypatch):
    svc,_,_=profile
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE','private-profile-code-123')
    app.dependency_overrides[athlete_profile.service]=lambda:svc
    client=TestClient(app)
    headers={'Authorization':'Bearer private-profile-code-123'}
    try:
        assert client.get('/coach/profile').status_code==401
        initial=client.get('/coach/profile',headers=headers)
        assert initial.status_code==200 and initial.headers['cache-control']=='no-store'
        body={'id':str(uuid4()),'version':initial.json()['version'],'change':memory()}
        candidate=client.post('/coach/profile/proposals',headers=headers,json=body)
        assert candidate.status_code==200
        assert not svc.snapshot()['memory']
        assert client.post('/coach/profile/proposals/'+body['id']+'/decision',headers=headers,json={'decision':'accept'}).status_code==200
        invalid=body|{'id':str(uuid4()),'version':svc.snapshot()['version'],'change':{'kind':'cycle','cycle_days':7}}
        assert client.post('/coach/profile/proposals',headers=headers,json=invalid).status_code==422
    finally:
        app.dependency_overrides.pop(athlete_profile.service)


def test_planner_requires_confirmed_goal_and_uses_selected_a_not_first_a(profile):
    from app.services.race_plan_service import RacePlanService
    svc,factory,source=profile
    source.correction_snapshot=lambda:{'source':['sheet','1'], 'headers':['date','title','description','planned_distance_km','planned_duration_min','priority'], 'rows':[]}
    planner=RacePlanService(source,factory,now=lambda:datetime(2026,11,7))
    with pytest.raises(ChatError,match='potwierdź cel'):
        planner.context()
    chosen=propose(svc,goal_change(svc))
    svc.decide(chosen['id'],True)
    source.rows[1]['priority']='A'
    context=planner.context()
    assert context['default_end']=='2027-03-28'
    source.rows[0]['target_time']='39:00'
    with pytest.raises(ChatError,match='zmienił się'):
        planner.context()
    assert CurrentGoalService(factory).get().target_time_sec==2310


def test_confirmed_cycle_anchor_controls_personal_coach_offset(profile):
    from app.services.personal_plan_coach import PersonalPlanCoach
    svc,_,_=profile
    selected=propose(svc,{'kind':'cycle','cycle_days':10,'anchor_date':'2026-11-01'})
    svc.decide(selected['id'],True)
    class Model:
        def generate(self,**kwargs):
            return json.dumps({'cycle_days':10,'status':'ready','health':'clear','start_offset':0,
                'anchor_note':'Propozycja dnia pierwszego','explanation':'Wybór na podstawie historii.', 'evidence':['history'],'questions':[],
                'days':[{'offset':i,'kind':'easy' if i in (0,5) else 'off','distance_km':5 if i in (0,5) else 0,
                         'duration_min':30 if i in (0,5) else 0,'reason':'Spokojne obciążenie'} for i in range(10)]})
    context={'facts':{'profile':svc.snapshot()},'planning_start':'2026-11-08','sources':[{'id':'history'}],
             'limits':{'history_sufficient':True,'max_cycle_km':30,'max_session_km':10,'max_session_minutes':90}}
    strategy=PersonalPlanCoach(Model()).propose(context,[],'')
    assert strategy['start_offset']==7
    assert 'potwierdzony cykl' in strategy['anchor_note']


def test_profile_source_requires_both_quote_and_turn_identifier(profile,monkeypatch):
    svc,_,_=profile
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE','private-profile-code-123')
    app.dependency_overrides[athlete_profile.service]=lambda:svc
    try:
        response=TestClient(app).post('/coach/profile/proposals',headers={'Authorization':'Bearer private-profile-code-123'},
            json={'id':str(uuid4()),'version':svc.snapshot()['version'],'change':memory(),'quote':'Wymyślone źródło'})
        assert response.status_code==422
    finally:
        app.dependency_overrides.pop(athlete_profile.service)


def test_completed_goal_is_not_silently_replaced_by_the_next_a(profile):
    from app.services.race_plan_service import RacePlanService
    svc,factory,source=profile
    selected=propose(svc,goal_change(svc))
    svc.decide(selected['id'],True)
    source.correction_snapshot=lambda:{'source':['sheet','1'], 'headers':['date','title','description','planned_distance_km','planned_duration_min','priority'], 'rows':[]}
    source.rows.append(dict(source.rows[0],date='2027-05-01',name='Następny start'))
    planner=RacePlanService(source,factory,now=lambda:datetime(2027,3,22))
    with pytest.raises(ChatError,match='już minął'):
        planner.context()
    assert CurrentGoalService(factory).get().target_date==date(2027,3,21)
