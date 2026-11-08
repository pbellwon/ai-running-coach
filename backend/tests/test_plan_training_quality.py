from copy import deepcopy
from datetime import date,datetime,timedelta
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import WorkoutDB,LapDB,WorkoutFeedbackDB
from app.engine.planned_workout_engine import PlannedWorkoutEngine
from app.engine.race_plan_engine import RacePlanEngine
from app.services.personal_plan_context import PersonalPlanContext
from app.services.personal_plan_coach import PersonalPlanCoach,Strategy
from test_race_plans import strategy


def trained_strategy(reps=3,work=10):
    result=strategy()
    result['days'][2].update(repetitions=reps,work_min=work,recovery_min=2 if reps>1 else 0,
                            duration_min=60,distance_km=10)
    result['days'][9].update(kind='strength',distance_km=0,duration_min=30,
        strength_exercises=['Split squat 2 x 6 na stronę','Hip hinge 2 x 8','Plank boczny 2 x 20 s'])
    return result


LIMITS={'history_sufficient':True,'max_cycle_km':60,'max_session_km':18,'max_session_minutes':100,
        'strength_required':True,'max_strength_minutes':30,'observed_threshold_work_min':30}


@pytest.fixture
def history():
    engine=create_engine('sqlite://',poolclass=StaticPool)
    Base.metadata.create_all(engine);factory=sessionmaker(bind=engine)
    with factory() as db:
        db.add(WorkoutDB(source_file='threshold.fit',start_time=datetime(2026,10,20,8),sport='running',
            declared_workout_type='threshold',activity_name='3 x 10 min threshold',distance_km=11.8,duration_sec=52*60))
        db.add(WorkoutDB(source_file='gym.fit',start_time=datetime(2026,10,22,8),sport='training',
            declared_workout_type='strength',distance_km=0,duration_sec=30*60))
        for index,(seconds,meters) in enumerate([(600,2000),(600,2500),(120,400),(600,2500),(120,400),(600,2500),(480,1500)],1):
            db.add(LapDB(workout_file='threshold.fit',lap_number=index,elapsed_time_sec=seconds,distance_m=meters,avg_hr=165 if meters==2500 else 130))
        db.add(WorkoutFeedbackDB(session_id='session:threshold.fit',perceived_effort=6,execution_feeling='as_expected',
            created_at=datetime(2026,10,20),updated_at=datetime(2026,10,20)))
        db.commit()
    yield factory
    engine.dispose()


def test_context_uses_actual_work_intervals_and_versions_laps(history):
    service=PersonalPlanContext(history)
    context=service.capture(date(2026,11,1))
    evidence=context['facts']['training_evidence']
    assert evidence['threshold_sessions'][0]['work_min']==30
    assert evidence['threshold_sessions'][0]['blocks_min']==[10,10,10]
    assert context['limits']['observed_threshold_work_min']==30
    assert context['limits']['max_strength_minutes']==30
    with history() as db:
        db.query(LapDB).filter_by(lap_number=2).update({'elapsed_time_sec':599});db.commit()
    assert service.capture(date(2026,11,1))['version']!=context['version']


def test_bad_feedback_does_not_become_a_positive_reference(history):
    with history() as db:
        db.query(WorkoutFeedbackDB).update({'execution_feeling':'too_hard'});db.commit()
    context=PersonalPlanContext(history).capture(date(2026,11,1))
    assert context['facts']['training_evidence']['threshold_sessions'][0]['feedback_concern']
    assert context['limits']['observed_threshold_work_min']==0


def test_missing_laps_do_not_turn_a_52_minute_session_or_title_into_work_dose(history):
    with history() as db: db.query(LapDB).delete();db.commit()
    context=PersonalPlanContext(history).capture(date(2026,11,1))
    assert context['limits']['observed_threshold_work_min']==0
    assert context['facts']['training_evidence']['threshold_sessions']==[]


def test_strength_and_continuous_threshold_are_supported():
    candidate=Strategy.model_validate(trained_strategy(reps=1,work=30))
    PersonalPlanCoach.validate(candidate,{'sources':[{'id':'history'},{'id':'memory:1'}],'limits':LIMITS})
    assert candidate.days[9].kind=='strength'


@pytest.mark.parametrize('change',['missing','duration','adjacent','running_distance','dose'])
def test_quality_rules_reject_missing_strength_conflicts_or_unobserved_first_dose(change):
    value=trained_strategy()
    if change=='missing':value['days'][9].update(kind='off',duration_min=0,strength_exercises=[])
    elif change=='duration':value['days'][9]['duration_min']=45
    elif change=='running_distance':value['days'][9]['distance_km']=5
    elif change=='adjacent':value['days'][1],value['days'][9]=dict(value['days'][9],offset=1),dict(value['days'][1],offset=9)
    else:value['days'][2].update(repetitions=3,work_min=15,duration_min=75)
    with pytest.raises(ValueError):PersonalPlanCoach.validate(Strategy.model_validate(value),{'sources':[{'id':'history'},{'id':'memory:1'}],'limits':LIMITS})


def build_plan(candidate):
    goal={'date':'2027-03-14','name':'Półmaraton','distance_km':21.1,'priority':'A','target_time':'1:27:30','notes':''}
    return RacePlanEngine().build({'source':['sheet','1'],'headers':['date','title','description','planned_distance_km','planned_duration_min','priority'],'rows':[]},
        [goal],candidate,date(2026,12,1),date(2027,3,21),True,set(),date(2026,11,8),LIMITS,goal)


def test_experienced_half_marathon_plan_has_strength_and_substantial_threshold_not_fixed_two_by_eight():
    plan=build_plan(trained_strategy())
    thresholds=[e for e in plan['entries'] if e['threshold_work_min']]
    assert max(e['threshold_work_min'] for e in thresholds)>=30
    assert all(re.search(r'3 x \d+ min threshold',e['after']['description']) for e in thresholds)
    strength=[e for e in plan['entries'] if e['after']['title']=='Trening siłowy dla biegacza']
    assert len(strength)>=6
    assert all(e['after']['planned_distance_km']=='0' and e['after']['planned_duration_min']=='30' for e in strength)
    assert all('Split squat 2 x 6' in e['after']['description'] for e in strength)
    assert all(PlannedWorkoutEngine().build(date.fromisoformat(e['after']['date']),e['after']['title'],e['after']['description']).workout_type=='strength' for e in strength)
    assert all(abs((date.fromisoformat(s['after']['date'])-date.fromisoformat(t['after']['date'])).days)>=2 for s in strength for t in thresholds)
    assert any(c['strength_sessions'] and c['threshold_work_min'] for c in plan['cycles'])


def test_short_return_seed_can_rebuild_toward_recorded_history_over_months():
    plan=build_plan(trained_strategy(reps=2,work=4))
    thresholds=[e for e in plan['entries'] if e['threshold_work_min']]
    assert max(e['threshold_work_min'] for e in thresholds if e['after']['date']<'2026-12-11')<=8
    assert max(e['threshold_work_min'] for e in thresholds)>=24
    assert all(e['threshold_work_min']<=36 for e in thresholds)
    for entry in thresholds:
        row=entry['after'];match=re.search(r'(\d+) x (\d+) min threshold',row['description'])
        reps,minutes=map(int,match.groups())
        assert 18+reps*minutes+(reps-1)*2<=int(row['planned_duration_min'])


def test_revision_in_specific_phase_still_respects_current_reduced_seed_in_its_first_cycle():
    goal={'date':'2027-03-14','name':'Półmaraton','distance_km':21.1,'priority':'A','target_time':'1:27:30','notes':''}
    plan=RacePlanEngine().build({'source':['sheet','1'],'headers':['date','title','description','planned_distance_km','planned_duration_min','priority'],'rows':[]},
        [goal],trained_strategy(reps=2,work=4),date(2027,2,10),date(2027,3,21),True,set(),date(2027,2,9),LIMITS,goal,date(2026,12,1))
    first=[e for e in plan['entries'] if e['after']['date']<'2027-02-20' and e['threshold_work_min']]
    assert first and max(e['threshold_work_min'] for e in first)<=8
