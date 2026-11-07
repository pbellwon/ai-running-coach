from datetime import date,timedelta
from app.engine.long_term_plan import LongTermPlan
from app.engine.race_plan_engine import RacePlanEngine


def seed():
    return {'start_offset':0,'days':[{'offset':i,'kind':{0:'easy',2:'threshold',4:'easy',6:'long',8:'easy'}.get(i,'off'),
        'distance_km':12 if i==6 else 8 if i==2 else 6 if i in (0,4,8) else 0,
        'duration_min':72 if i==6 else 48 if i==2 else 36 if i in (0,4,8) else 0,
        'repetitions':3 if i==2 else 0,'work_min':4 if i==2 else 0,'recovery_min':2 if i==2 else 0,'reason':'Historia tolerancji.'} for i in range(10)]}


def event(day='2027-03-21',priority='A',distance=10):
    return {'date':day,'name':'Start '+priority,'distance_km':distance,'priority':priority,'target_time':'','notes':''}


def build(events=None,goal=None):
    events=events or [event()]
    goal=goal or events[-1]
    return RacePlanEngine().build({'source':['sheet','1'],'headers':['date','title','description','planned_distance_km','planned_duration_min','priority'],'rows':[]},
        events,seed(),date(2026,12,1),date(2027,3,28),True,set(),date(2026,11,7),{'max_session_km':15,'max_session_minutes':90},goal)


def test_december_to_march_has_complete_arc_and_every_day():
    result=build()
    phases=result['long_term']['phases']
    assert [p['key'] for p in phases]==['foundation','development','specific','taper','recovery']
    assert phases[0]['start']=='2026-12-01' and phases[-1]['end']=='2027-03-28'
    assert len(result['entries'])==(date(2027,3,28)-date(2026,12,1)).days+1
    assert len({e['after']['date'] for e in result['entries']})==len(result['entries'])
    assert all(c['role'] and c['checkpoint'] for c in result['cycles'])
    for entry in result['entries']:
        if not entry['after']['title'].startswith('Zawody') and entry['after']['planned_distance_km'] != '0':
            phase=next(p for p in phases if p['start'] <= entry['after']['date'] <= p['end'])
            assert phase['role'] in entry['after']['description']
    assert result['cycles'][1]['start']=='2026-12-11'


def test_cycles_have_different_doses_not_one_repeated_template():
    result=build()
    before=[e for e in result['entries'] if e['after']['date']<'2027-03-11']
    threshold=[e for e in before if e['after']['title']=='Bieg progowy kontrolowany']
    assert threshold
    assert all(e['after']['date']>='2027-01-01' for e in threshold)
    assert len({e['after']['description'].split('\nPaceMind')[0] for e in threshold})>1
    assert max(c['budget_km'] for c in result['cycles'])>result['cycles'][0]['budget_km']
    assert any('odciążenie' in c['phase'] for c in result['cycles'])


def test_progression_respects_previous_peak_and_taper_reduces_budget():
    campaign=LongTermPlan(date(2026,12,1),date(2027,3,28),seed(),[event()],{},event())
    peak=None
    normal=[]
    for i in range(12):
        cycle=campaign.cycle(date(2026,12,1)+timedelta(days=10*i),i)
        if cycle['phase_key'] in ('foundation','development','specific') and not cycle['deload']:
            if peak: assert cycle['factor']<=peak*1.04+1e-9
            peak=cycle['factor'];normal.append(peak)
        elif cycle['phase_key']=='taper': assert cycle['factor']<max(normal)


def test_selected_main_a_is_not_replaced_by_control_races():
    main=event()
    result=build([event('2027-01-10','A'),event('2027-02-14','B'),event('2027-03-01','C'),main],main)
    assert result['long_term']['goal']['date']=='2027-03-21'
    races=[e for e in result['entries'] if e['after']['title'].startswith('Zawody')]
    assert len(races)==4
    assert result['long_term']['phases'][-2]['end']=='2027-03-21'
    for entry in result['entries']:
        day=entry['after']['date']
        if '2027-03-11'<=day<'2027-03-21': assert entry['after']['title']!='Bieg progowy kontrolowany'
        if '2027-03-22'<=day<='2027-03-23': assert entry['after']['planned_distance_km']=='0'


def test_short_horizon_reports_missing_preparation_instead_of_inventing_it():
    main=event('2026-12-10')
    campaign=LongTermPlan(date(2026,12,1),date(2026,12,12),seed(),[main],{},main)
    result=campaign.manifest()
    assert result['warnings'] and result['phases'][0]['key']=='taper'


def test_quality_progression_is_bounded_by_personal_seed_not_generic_dose():
    template=seed()
    template['days'][2].update(repetitions=2,work_min=2,recovery_min=1)
    campaign=LongTermPlan(date(2026,12,1),date(2027,3,28),template,[event()],{},event())
    for i in range(12):
        cycle=campaign.cycle(date(2026,12,1)+timedelta(days=10*i),i)
        for unit in campaign.pattern(cycle).values():
            if unit['kind']=='threshold':
                assert unit['repetitions']*unit['work_min']<=4*cycle['envelope']
