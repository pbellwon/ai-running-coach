from copy import deepcopy
from datetime import date, datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.db.models import CoachChatGateDB, WorkoutDB, AthleteMemoryDB, WorkoutFeedbackDB
from app.api import race_plans
from app.main import app
from app.engine.race_plan_engine import MARKER, parse_calendar
from app.services.race_plan_service import RacePlanService
from app.services.plan_correction_service import PlanCorrectionService, digest
from app.services.personal_plan_context import PersonalPlanContext
from app.services.personal_plan_coach import PersonalPlanCoach
from app.services.coach_chat_service import ChatError
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource

HEADERS = ['date', 'title', 'description', 'planned_distance_km', 'planned_duration_min', 'priority', 'uwagi']
RACE_HEADERS = ['date', 'name', 'distance_km', 'priority', 'target_time', 'notes']
TODAY = date(2026, 11, 1)

def row(day='2026-11-03', **updates):
    return {'date': day, 'title': 'Threshold', 'description': '3 x 10 min threshold\nUwagi trenera: zachowaj.', 'planned_distance_km': '10', 'planned_duration_min': '60', 'priority': 'key', 'uwagi': '=literal'} | updates

def calendar_row(day='2026-12-13', **updates):
    return {'date': day, 'name': 'Bieg <img src=x>', 'distance_km': '10', 'priority': 'A', 'target_time': '38:30', 'notes': 'Trasa płaska'} | updates

def strategy():
    days = []
    for offset in range(10):
        kind = {0: 'easy', 2: 'threshold', 4: 'easy', 6: 'long', 8: 'easy'}.get(offset, 'off')
        km = {'easy': 6, 'threshold': 8, 'long': 12, 'off': 0}[kind]
        days.append({'offset': offset, 'kind': kind, 'distance_km': km, 'duration_min': int(km*6), 'repetitions': 3 if kind == 'threshold' else 0, 'work_min': 4 if kind == 'threshold' else 0, 'recovery_min': 2 if kind == 'threshold' else 0, 'reason': 'Układ zgodny z historią i regeneracją.'})
    return {'cycle_days': 10, 'status': 'ready', 'health': 'historical', 'start_offset': 0, 'anchor_note': 'Proponuję nowy cykl od jutra.', 'explanation': 'Historia wspiera rozłożone bodźce; to nie dowód przyczynowy.', 'evidence': ['history', 'memory:1'], 'questions': [], 'days': days}

class Model:
    def __init__(self): self.value, self.calls, self.input = strategy(), 0, None
    def generate(self, **kwargs):
        self.calls += 1
        self.input = json.loads(kwargs['input_text'])
        return json.dumps(self.value)

class Athlete:
    def __init__(self): self.change = ''
    def capture(self, today):
        return {'version': digest(self.change), 'facts': {'memory': ['Dawna kontuzja, zakończony powrót.'], 'conversations': ['Cykl 10 dni'], 'feedback': []}, 'sources': [{'id': 'history', 'label': 'Historia 84 dni'}, {'id': 'memory:1', 'label': 'Pamięć kontuzji'}], 'limitations': ['Tylko rozmowy PaceMind'], 'limits': {'cycle_days': 10, 'max_cycle_km': 45, 'max_session_km': 15, 'max_session_minutes': 90, 'history_sufficient': True}}

class Sheet:
    def __init__(self):
        self.plan = {'source': ['test', '1'], 'headers': HEADERS, 'rows': [row()]}
        self.calendar = {'source': ['test', '2'], 'headers': RACE_HEADERS, 'rows': [calendar_row()]}
        self.writes, self.single_writes, self.failure = 0, 0, None
    def correction_snapshot(self): return deepcopy(self.plan)
    def race_calendar_snapshot(self): return deepcopy(self.calendar)
    def write_generated_plan(self, before, after):
        self.writes += 1
        if self.failure == 'before': raise TimeoutError()
        self.plan = deepcopy(after)
        if self.failure == 'after': raise TimeoutError()
    def write_correction(self, snapshot, row_number, before, after):
        self.single_writes += 1
        self.plan['rows'][row_number-2] = deepcopy(after)

@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sheet, model, athlete = Sheet(), Model(), Athlete()
    svc = RacePlanService(sheet, factory, now=lambda: datetime(2026, 11, 1, 12), athlete_context=athlete, coach=PersonalPlanCoach(model))
    yield svc, sheet, factory, model, athlete
    engine.dispose()

def request(svc, **changes):
    return {'plan_version': digest(svc.source.plan), 'calendar_version': digest(svc.source.calendar), 'athlete_version': svc.athlete_context.capture(TODAY)['version'], 'start': '2026-11-02', 'end': '2026-12-20', 'replace_existing': True, 'note': ''} | changes

def preview(svc, **changes):
    with svc.factory() as db:
        db.query(CoachChatGateDB).update({'next_allowed_at': datetime(2000, 1, 1)})
        db.commit()
    return svc.preview(str(uuid4()), request(svc, **changes))

def test_calendar_validation_and_comma_distance():
    snapshot = {'headers': RACE_HEADERS, 'rows': [calendar_row(distance_km='21,1', priority='b')]}
    assert parse_calendar(snapshot)[0]['distance_km'] == 21.1
    for value in ['NaN', 'inf', '-1', '']:
        snapshot['rows'][0]['distance_km'] = value
        with pytest.raises(ChatError): parse_calendar(snapshot)

@pytest.mark.parametrize('changes', [{'date': '13.12.2026'}, {'priority': 'X'}, {'target_time': '38:99'}, {'name': ''}])
def test_invalid_calendar_fails_closed(changes):
    with pytest.raises(ChatError): parse_calendar({'headers': RACE_HEADERS, 'rows': [calendar_row(**changes)]})

def test_ten_day_cycle_is_not_a_renamed_week(setup):
    svc, sheet, _, model, _ = setup
    item = preview(svc)
    assert sheet.writes == 0 and item['cycle_days'] == 10
    assert item['cycles'][0]['start'] == '2026-11-02' and item['cycles'][0]['end'] == '2026-11-11'
    assert item['cycles'][1]['start'] == '2026-11-12'
    assert [e['cycle_day'] for e in item['entries'][:20]] == list(range(1, 11))*2
    assert len(item['entries']) == 49
    assert item['coaching']['evidence'] == ['history', 'memory:1']
    assert model.input['context']['facts']['conversations'] == ['Cykl 10 dni']
    assert 'athlete_context' not in item
    assert all('cykl 10-dniowy' in e['after']['description'] for e in item['entries'])

def test_known_cycle_position_continues_without_monday_reset(setup):
    svc, _, _, model, _ = setup
    model.value['start_offset'] = 4
    item = preview(svc)
    assert item['entries'][0]['cycle_day'] == 5
    assert item['cycles'][0]['end'] == '2026-11-07' and item['cycles'][1]['start'] == '2026-11-08'

def test_preserve_corrections_multiple_units_and_original_notes(setup):
    svc, sheet, _, _, _ = setup
    sheet.plan['rows'] += [row('2026-11-04', description='Original'+MARKER+'Spokojny bieg\nPaceMind stara korekta'), row('2026-11-05'), row('2026-11-05')]
    item = preview(svc)
    assert item['summary']['kept'] == 3
    changed = next(e for e in item['entries'] if e['after']['date'] == '2026-11-03')
    assert changed['after']['description'].startswith(changed['before']['description']) and changed['after']['uwagi'] == '=literal'

@pytest.mark.parametrize('field', ['plan', 'calendar', 'athlete', 'date'])
def test_every_source_is_checked_before_acceptance(setup, field):
    svc, sheet, _, _, athlete = setup
    item = preview(svc)
    if field == 'plan': sheet.plan['rows'][0]['uwagi'] += ' changed'
    elif field == 'calendar': sheet.calendar['rows'][0]['target_time'] = '39:00'
    elif field == 'athlete': athlete.change = 'new pain report'
    else: svc.now = lambda: datetime(2026, 11, 2)
    with pytest.raises(ChatError): svc.decide(item['id'], True)
    assert sheet.writes == 0 and svc.get(item['id'])['status'] == 'stale'

def test_retries_do_not_repeat_ai_or_append_rows(setup):
    svc, sheet, _, model, _ = setup
    body, identifier = request(svc), str(uuid4())
    item = svc.preview(identifier, body)
    assert svc.preview(identifier, body) == item and model.calls == 1
    sheet.failure = 'after'
    assert svc.decide(identifier, True)['status'] == 'applied'
    assert svc.decide(identifier, True)['status'] == 'applied'
    assert sheet.writes == 1 and len(sheet.plan['rows']) == 49
    with pytest.raises(ChatError): svc.preview(identifier, body | {'note': 'inna treść'})

def test_uncertain_write_blocks_single_corrections(setup):
    svc, sheet, factory, _, _ = setup
    single = PlanCorrectionService(sheet, factory, now=svc.now)
    correction = single.preview(str(uuid4()), digest(sheet.plan), 2, {'title': 'Easy', 'planned_distance_km': 7, 'planned_duration_min': 42, 'description': 'Spokojny bieg'}, 'Zmęczenie')
    item = preview(svc)
    sheet.failure = 'before'
    with pytest.raises(ChatError): svc.decide(item['id'], True)
    with pytest.raises(ChatError): svc.decide(item['id'], True)
    with pytest.raises(ChatError): single.decide(correction['id'], True)
    assert sheet.writes == 1 and sheet.single_writes == 0

def test_shared_paid_ai_gate_prevents_duplicate_generation(setup):
    svc, _, _, model, _ = setup
    first = preview(svc)
    with pytest.raises(ChatError) as exc: svc.preview(str(uuid4()), request(svc))
    assert exc.value.status == 429 and model.calls == 1 and svc.get(first['id'])['can_accept']

def test_injury_uncertainty_asks_instead_of_generating(setup):
    svc, sheet, _, model, _ = setup
    model.value.update(status='clarify', health='unclear', questions=['Czy ból ścięgna nadal występuje?'], days=[])
    item = preview(svc)
    assert not item['can_accept'] and not item['entries']
    assert item['blockers'] == ['Czy ból ścięgna nadal występuje?']
    with pytest.raises(ChatError): svc.decide(item['id'], True)
    assert sheet.writes == 0

@pytest.mark.parametrize('invalid', ['health', 'cycle', 'volume', 'spacing', 'evidence', 'intervals'])
def test_unsafe_or_invented_model_output_is_rejected(setup, invalid):
    svc, sheet, _, model, _ = setup
    if invalid == 'health': model.value['health'] = 'active'
    elif invalid == 'cycle': model.value['cycle_days'] = 7
    elif invalid == 'volume': model.value['days'][0]['distance_km'] = 90
    elif invalid == 'spacing': model.value['days'][2]['offset'], model.value['days'][5]['offset'] = 5, 2
    elif invalid == 'evidence': model.value['evidence'] = ['invented']
    else: model.value['days'][2]['duration_min'] = 20
    with pytest.raises(ChatError) as error: preview(svc)
    assert error.value.status == 502 and sheet.writes == 0 and svc.history()['items'] == []

def test_insufficient_history_does_not_call_ai(setup):
    svc, _, _, model, athlete = setup
    original = athlete.capture
    def insufficient(today):
        result = original(today)
        result['limits']['history_sufficient'] = False
        return result
    athlete.capture = insufficient
    with pytest.raises(ChatError): preview(svc)
    assert model.calls == 0

def test_actual_memory_feedback_and_training_change_context_version(setup):
    _, _, factory, _, _ = setup
    with factory() as db:
        for day in (15, 18, 21, 24, 27, 30): db.add(WorkoutDB(source_file=f'{day}.fit', start_time=datetime(2026, 10, day), sport='running', distance_km=8, duration_sec=2700, declared_workout_type='easy_run'))
        db.add(AthleteMemoryDB(category='injury', memory_text='Historia kontuzji Achillesa', source='athlete', is_active=True, created_at=datetime(2026, 10, 1), updated_at=datetime(2026, 10, 1)))
        db.add(WorkoutFeedbackDB(session_id='session', comment='Po akcentach mocne zmęczenie.', created_at=datetime(2026, 10, 30), updated_at=datetime(2026, 10, 30)))
        db.commit()
    context = PersonalPlanContext(factory)
    first = context.capture(TODAY)
    assert first['limits']['history_sufficient'] and first['limits']['max_cycle_km'] == 17.1
    assert 'Achillesa' in first['facts']['memory'][0]['memory_text'] and 'zmęczenie' in first['facts']['feedback'][0]['comment']
    with factory() as db:
        db.query(AthleteMemoryDB).update({'memory_text': 'Aktualny ból'})
        db.commit()
    assert context.capture(TODAY)['version'] != first['version']

def test_no_preferences_api_and_private_planning(setup, monkeypatch):
    svc, _, _, _, _ = setup
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', 'owner-code-long-enough')
    app.dependency_overrides[race_plans.service] = lambda: svc
    client, headers = TestClient(app), {'Authorization': 'Bearer owner-code-long-enough'}
    try:
        assert client.get('/coach/race-plans/context').status_code == 401
        context = client.get('/coach/race-plans/context', headers=headers).json()
        assert 'preferences' not in context and context['cycle_days'] == 10
        assert client.put('/coach/race-plans/preferences', json={}, headers=headers).status_code == 410
        assert client.post('/coach/race-plans/preview', json={'id': str(uuid4()), **request(svc)}, headers=headers).status_code == 200
    finally: app.dependency_overrides.pop(race_plans.service)

def test_races_taper_recovery_and_atomic_literal_write(setup):
    svc, sheet, _, _, _ = setup
    item = preview(svc)
    assert any('Taper' in c['phase'] for c in item['cycles'])
    for entry in item['entries']:
        if '2026-12-14' <= entry['after']['date'] <= '2026-12-15': assert entry['after']['planned_distance_km'] == '0'
    source = GoogleSheetsPlanSource('test', 'plan_import', 'unused')
    worksheet = Mock(id=1, row_count=2)
    source._correction_worksheet = lambda: worksheet
    before = sheet.plan
    after = deepcopy(before)
    after['rows'][0]['description'] = '=literal text'
    after['rows'].append(row('2026-11-04'))
    source.write_generated_plan(before, after)
    requests = worksheet.spreadsheet.batch_update.call_args.args[0]['requests']
    assert requests[0]['appendDimension']['length'] == 1
    assert requests[1]['updateCells']['rows'][0]['values'][0]['userEnteredValue'] == {'stringValue': '=literal text'}


def test_legacy_preview_is_readable_but_cannot_be_applied(setup):
    from app.db.models import RacePlanDraftDB
    svc, sheet, factory, _, _ = setup
    item = preview(svc)
    with factory() as db:
        record = db.get(RacePlanDraftDB, item['id'])
        payload = json.loads(record.payload)
        payload.pop('planning_mode')
        record.payload = json.dumps(payload)
        db.commit()
    assert svc.get(item['id'])['id'] == item['id']
    with pytest.raises(ChatError, match='starego generatora'):
        svc.decide(item['id'], True)
    assert sheet.writes == 0
    assert svc.decide(item['id'], False)['status'] == 'rejected'


def test_old_health_and_cycle_conversations_survive_recent_window(setup):
    from app.db.models import CoachConversationDB, CoachChatTurnDB
    _, _, factory, _, _ = setup
    with factory() as db:
        conversation = str(uuid4())
        db.add(CoachConversationDB(id=conversation, title='Rozmowa', created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 11, 1)))
        for index in range(65):
            db.add(CoachChatTurnDB(id=str(uuid4()), conversation_id=conversation, request_hash='hash',
                message='Kontuzja Achillesa, omawiam cykl 10-dniowy.' if index == 0 else 'Co z treningiem?',
                answer='To interpretacja trenera.', context_json='{}', status='completed', lease='',
                created_at=datetime(2026, 10, 1)+timedelta(hours=index),
                updated_at=datetime(2026, 10, 1)))
        db.commit()
    captured = PersonalPlanContext(factory).capture(TODAY)
    assert any('Achillesa' in c['message'] for c in captured['facts']['conversations'])
    assert any('10-dniowy' in c['message'] for c in captured['facts']['conversations'])
    assert len(captured['facts']['conversations']) == 61


def test_changed_feedback_invalidates_previously_seen_context(setup):
    _, _, factory, _, _ = setup
    context = PersonalPlanContext(factory)
    first = context.capture(TODAY)
    with factory() as db:
        db.add(WorkoutFeedbackDB(session_id='new', comment='Aktualny ból', created_at=datetime(2026, 11, 1), updated_at=datetime(2026, 11, 1)))
        db.commit()
    assert context.capture(TODAY)['version'] != first['version']
