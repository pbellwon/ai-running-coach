from copy import deepcopy
from datetime import date, datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.db.models import PlanCorrectionDB, PlanWriteGateDB
from app.api import race_plans
from app.main import app
from app.engine.race_plan_engine import RacePlanEngine, parse_calendar, MARKER
from app.services.race_plan_service import RacePlanService
from app.services.plan_correction_service import PlanCorrectionService, digest
from app.services.coach_chat_service import ChatError
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource

PREFS = {'weekdays': [1, 3, 5, 6], 'long_run_day': 6, 'weekly_distance_km': 40.0,
         'easy_pace_min_km': 6.0, 'max_minutes': {str(i): 90 if i == 6 else 60 for i in range(7)}}
HEADERS = ['date', 'title', 'description', 'planned_distance_km', 'planned_duration_min', 'priority', 'uwagi']
RACE_HEADERS = ['date', 'name', 'distance_km', 'priority', 'target_time', 'notes']
TODAY = date(2026, 11, 1)


def row(day='2026-11-03', **updates):
    return {'date': day, 'title': 'Threshold', 'description': '3 x 10 min threshold\nUwagi trenera: zachowaj.',
            'planned_distance_km': '10', 'planned_duration_min': '60', 'priority': 'key', 'uwagi': '=literal'} | updates


def calendar_row(day='2026-12-13', **updates):
    return {'date': day, 'name': 'Bieg <img src=x>', 'distance_km': '10', 'priority': 'A', 'target_time': '38:30', 'notes': 'Trasa płaska'} | updates


class Sheet:
    def __init__(self):
        self.plan = {'source': ['test', '1'], 'headers': HEADERS, 'rows': [row()]}
        self.calendar = {'source': ['test', '2'], 'headers': RACE_HEADERS, 'rows': [calendar_row()]}
        self.writes, self.single_writes = 0, 0
        self.failure = None
    def correction_snapshot(self):
        return deepcopy(self.plan)
    def race_calendar_snapshot(self):
        return deepcopy(self.calendar)
    def write_generated_plan(self, before, after):
        self.writes += 1
        if self.failure == 'before':
            raise TimeoutError()
        self.plan = deepcopy(after)
        if self.failure == 'after':
            raise TimeoutError()
    def write_correction(self, snapshot, row_number, before, after):
        self.single_writes += 1
        self.plan['rows'][row_number - 2] = deepcopy(after)


@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sheet = Sheet()
    svc = RacePlanService(sheet, factory, now=lambda: datetime(2026, 11, 1, 12))
    svc.save_preferences(PREFS, digest(None))
    yield svc, sheet, factory
    engine.dispose()


def request(svc, **changes):
    return {'plan_version': digest(svc.source.plan), 'calendar_version': digest(svc.source.calendar),
            'preferences_version': svc.preferences()['version'], 'start': '2026-11-02',
            'end': '2026-12-20', 'replace_existing': False} | changes


def preview(svc, **changes):
    return svc.preview(str(uuid4()), request(svc, **changes))


def test_calendar_validation_and_comma_distance():
    snapshot = {'headers': RACE_HEADERS, 'rows': [calendar_row(distance_km='21,1', priority='b')]}
    assert parse_calendar(snapshot)[0]['distance_km'] == 21.1
    for value in ['NaN', 'inf', '-1', '']:
        snapshot['rows'][0]['distance_km'] = value
        with pytest.raises(ChatError):
            parse_calendar(snapshot)


@pytest.mark.parametrize('changes', [{'date': '13.12.2026'}, {'priority': 'X'}, {'target_time': '38:99'}, {'name': ''}])
def test_invalid_calendar_fails_closed(changes):
    with pytest.raises(ChatError):
        parse_calendar({'headers': RACE_HEADERS, 'rows': [calendar_row(**changes)]})


def test_calendar_duplicates_and_missing_headers():
    for snapshot in [{'headers': [], 'rows': []}, {'headers': RACE_HEADERS, 'rows': [calendar_row(), calendar_row()]}]:
        with pytest.raises(ChatError):
            parse_calendar(snapshot)


def test_complete_plan_has_race_taper_recovery_and_time_caps(setup):
    svc, sheet, _ = setup
    plan = preview(svc)
    assert sheet.writes == 0
    assert len({e['after']['date'] for e in plan['entries']}) == 49
    assert any('Taper' in w['phase'] for w in plan['weeks'])
    assert any('Specyfika startowa' in w['phase'] for w in plan['weeks'])
    assert any('lżejszy' in w['phase'] for w in plan['weeks'])
    assert next(e for e in plan['entries'] if e['after']['date'] == '2026-12-13')['after']['planned_distance_km'] == '10'
    for entry in plan['entries']:
        after = entry['after']
        day = date.fromisoformat(after['date'])
        if entry['action'] != 'keep' and not after['title'].startswith('Zawody'):
            assert int(after['planned_duration_min']) <= PREFS['max_minutes'][str(day.weekday())]
            if day.weekday() not in PREFS['weekdays'] or date(2026, 12, 14) <= day <= date(2026, 12, 15):
                assert after['planned_distance_km'] == '0'
        if entry['action'] != 'keep':
            assert after['description'].splitlines()[-1].startswith('PaceMind 2026-11-01 | Zmiana:')
    assert plan['summary']['kept'] == 1
    assert 'before_snapshot' not in plan
    # Classifications consume active prescriptions, not audit notes or old workouts.
    types = {RacePlanEngine._type(e['after']) for e in plan['entries']}
    assert {'race', 'off', 'easy_run', 'threshold'} <= types


def test_rebuild_preserves_corrections_multisessions_and_original_notes(setup):
    svc, sheet, _ = setup
    sheet.plan['rows'] += [row('2026-11-04', description='Original' + MARKER + 'Spokojny bieg\nPaceMind stara korekta'),
                           row('2026-11-05'), row('2026-11-05')]
    result = preview(svc, replace_existing=True)
    assert result['summary']['kept'] == 3
    replaced = next(e for e in result['entries'] if e['after']['date'] == '2026-11-03')
    assert replaced['action'] == 'replace'
    assert replaced['after']['description'].startswith(replaced['before']['description'])
    assert replaced['after']['uwagi'] == '=literal'
    assert result['can_accept']


def test_missing_a_or_invalid_period_blocks_generation(setup):
    svc, sheet, _ = setup
    for changes in [{'start': '2026-11-01'}, {'end': '2026-11-20'}, {'end': '2028-01-01'}]:
        with pytest.raises(ChatError):
            preview(svc, **changes)
    sheet.calendar['rows'][0]['priority'] = 'C'
    with pytest.raises(ChatError):
        preview(svc)


def test_preserved_race_conflict_blocks_acceptance(setup):
    svc, sheet, _ = setup
    sheet.plan['rows'].append(row('2026-12-13'))
    item = preview(svc)
    assert not item['can_accept'] and item['blockers']
    with pytest.raises(ChatError):
        svc.decide(item['id'], True)
    assert sheet.writes == 0
    assert preview(svc, replace_existing=True)['can_accept']


def test_apply_idempotent_and_history_survives_restart(setup):
    svc, sheet, factory = setup
    item = preview(svc)
    assert svc.decide(item['id'], True)['status'] == 'applied'
    restarted = RacePlanService(sheet, factory, now=svc.now)
    assert restarted.decide(item['id'], True)['status'] == 'applied'
    assert sheet.writes == 1
    assert restarted.history()['items'][0]['id'] == item['id']
    assert restarted.get(item['id'])['entries'] == item['entries']
    assert sheet.plan['rows'][0] == item['entries'][1]['before']


@pytest.mark.parametrize('what', ['plan', 'calendar', 'preferences', 'date'])
def test_stale_sources_block_acceptance(setup, what):
    svc, sheet, _ = setup
    item = preview(svc)
    if what == 'plan':
        sheet.plan['rows'][0]['uwagi'] += ' zmiana'
    elif what == 'calendar':
        sheet.calendar['rows'][0]['target_time'] = '39:00'
    elif what == 'preferences':
        svc.save_preferences(PREFS | {'weekly_distance_km': 35}, svc.preferences()['version'])
    else:
        svc.now = lambda: datetime(2026, 11, 2)
    with pytest.raises(ChatError):
        svc.decide(item['id'], True)
    assert sheet.writes == 0
    assert svc.get(item['id'])['status'] == 'stale'


def test_rejection_conflicting_decision_and_request_id(setup):
    svc, sheet, _ = setup
    identifier, body = str(uuid4()), request(svc)
    first = svc.preview(identifier, body)
    assert svc.preview(identifier, body) == first
    with pytest.raises(ChatError):
        svc.preview(identifier, body | {'replace_existing': True})
    assert svc.decide(identifier, False)['status'] == 'rejected'
    assert svc.decide(identifier, False)['status'] == 'rejected'
    with pytest.raises(ChatError):
        svc.decide(identifier, True)
    assert sheet.writes == 0


def test_lost_response_does_not_append_twice(setup):
    svc, sheet, _ = setup
    item = preview(svc)
    sheet.failure = 'after'
    assert svc.decide(item['id'], True)['status'] == 'applied'
    assert svc.decide(item['id'], True)['status'] == 'applied'
    assert len(sheet.plan['rows']) == 49
    assert sheet.writes == 1


def test_uncertain_full_write_blocks_single_corrections(setup):
    svc, sheet, factory = setup
    single = PlanCorrectionService(sheet, factory, now=svc.now)
    correction = single.preview(str(uuid4()), digest(sheet.plan), 2,
        {'title': 'Spokojny bieg', 'planned_distance_km': 7, 'planned_duration_min': 42, 'description': 'Spokojny bieg 7 km.'}, 'Zmęczenie')
    full = preview(svc)
    sheet.failure = 'before'
    with pytest.raises(ChatError, match='niepotwierdzony'):
        svc.decide(full['id'], True)
    with pytest.raises(ChatError):
        svc.decide(full['id'], True)
    with pytest.raises(ChatError, match='Inny zapis'):
        single.decide(correction['id'], True)
    assert sheet.writes == 1 and sheet.single_writes == 0


def test_single_correction_write_blocks_full_plan_and_marks_it_stale(setup):
    svc, sheet, factory = setup
    item = preview(svc)
    with factory() as db:
        db.add(PlanWriteGateDB(id=1, owner='other-write'))
        db.commit()
    with pytest.raises(ChatError, match='Inny zapis'):
        svc.decide(item['id'], True)
    assert sheet.writes == 0


def test_rebuilding_already_generated_rows_is_possible(setup):
    svc, sheet, _ = setup
    first = preview(svc, replace_existing=True)
    svc.decide(first['id'], True)
    second = preview(svc, replace_existing=True)
    assert second['summary']['replaced'] == 49
    assert second['summary']['kept'] == 0


def test_preference_validation_and_api_auth(setup, monkeypatch):
    svc, sheet, _ = setup
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', 'owner-code-long-enough')
    app.dependency_overrides[race_plans.service] = lambda: svc
    client = TestClient(app)
    headers = {'Authorization': 'Bearer owner-code-long-enough'}
    try:
        assert client.get('/coach/race-plans/context').status_code == 401
        assert client.get('/coach/race-plans/context', headers=headers).status_code == 200
        invalid = {'version': svc.preferences()['version'], 'value': PREFS | {'weekdays': [1, 1]}}
        assert client.put('/coach/race-plans/preferences', json=invalid, headers=headers).status_code == 422
        body = {'id': str(uuid4()), **request(svc)}
        response = client.post('/coach/race-plans/preview', json=body, headers=headers)
        assert response.status_code == 200
        assert client.get(f"/coach/race-plans/{body['id']}", headers=headers).status_code == 200
        applied = client.post(f"/coach/race-plans/{body['id']}/decision", json={'decision': 'accept'}, headers=headers)
        assert applied.status_code == 200 and applied.json()['status'] == 'applied'
    finally:
        app.dependency_overrides.pop(race_plans.service)


def test_bulk_writer_is_one_atomic_request_and_preserves_extra_columns():
    source = GoogleSheetsPlanSource('test', 'plan_import', 'unused')
    worksheet = Mock(id=1, row_count=2)
    source._correction_worksheet = lambda: worksheet
    before = {'source': ['test', '1'], 'headers': HEADERS, 'rows': [row()]}
    after = deepcopy(before)
    after['rows'][0]['description'] = '=literal text'
    after['rows'].append(row('2026-11-04'))
    source.write_generated_plan(before, after)
    worksheet.spreadsheet.batch_update.assert_called_once()
    requests = worksheet.spreadsheet.batch_update.call_args.args[0]['requests']
    assert requests[0]['appendDimension']['length'] == 1
    changed = requests[1]['updateCells']
    assert changed['rows'][0]['values'][0]['userEnteredValue'] == {'stringValue': '=literal text'}
    assert all('formulaValue' not in str(r) for r in requests)
    # Existing extra columns are not rewritten.
    assert not any(r.get('updateCells', {}).get('range', {}).get('startColumnIndex') == 6
                   and r.get('updateCells', {}).get('range', {}).get('startRowIndex') == 1 for r in requests)


def test_concurrent_full_plan_attempt_cannot_append_twice(setup):
    svc, sheet, _ = setup
    first, second = preview(svc), preview(svc)
    original = sheet.write_generated_plan
    def overlapping(before, after):
        with pytest.raises(ChatError, match='Inny zapis'):
            svc.decide(second['id'], True)
        original(before, after)
    sheet.write_generated_plan = overlapping
    svc.decide(first['id'], True)
    with pytest.raises(ChatError, match='nieaktualne'):
        svc.decide(second['id'], True)
    assert sheet.writes == 1
    assert len(sheet.plan['rows']) == 49


def test_priority_b_c_and_distance_dependent_recovery(setup):
    svc, sheet, _ = setup
    sheet.calendar['rows'] += [calendar_row('2026-11-15', priority='B', distance_km='21.1'),
                               calendar_row('2026-11-29', priority='C', distance_km='5')]
    result = preview(svc, replace_existing=True)
    assert any('startu B' in week['phase'] for week in result['weeks'])
    for entry in result['entries']:
        day = date.fromisoformat(entry['after']['date'])
        if date(2026, 11, 16) <= day <= date(2026, 11, 19):
            assert entry['after']['planned_distance_km'] == '0'
    races = [e for e in result['entries'] if e['after']['title'].startswith('Zawody:')]
    assert len(races) == 3
    assert {e['after']['planned_distance_km'] for e in races} == {'5', '10', '21.1'}


def test_generated_hard_sessions_have_spacing_across_weeks(setup):
    svc, sheet, _ = setup
    result = preview(svc, replace_existing=True)
    hard = [date.fromisoformat(e['after']['date']) for e in result['entries']
            if RacePlanEngine._type(e['after']) in ('threshold', 'race', 'long_run')]
    assert all((later - earlier).days >= 3 for earlier, later in zip(hard, hard[1:]))
    for week in result['weeks']:
        # No ordinary generated week exceeds its distance budget; a race may.
        if week['planned_km'] > week['budget_km'] + 0.5:
            assert any(e['priority'] for e in result['races']
                       if 0 <= (date.fromisoformat(e['date']) - date.fromisoformat(week['week_start'])).days <= 6)


def test_multiple_a_races_restart_preparation_cycles(setup):
    svc, sheet, _ = setup
    sheet.calendar['rows'].append(calendar_row('2027-03-21', name='Półmaraton', distance_km='21.1'))
    result = preview(svc, end='2027-03-28', replace_existing=True)
    assert any(w['phase'] == 'Budowanie' for w in result['weeks'])
    assert any(w['phase'] == 'Specyfika startowa' for w in result['weeks'])
    first_a = [w for w in result['weeks'] if w['week_start'] == '2026-12-07'][0]
    second_a = [w for w in result['weeks'] if w['week_start'] == '2027-03-15'][0]
    assert first_a['phase'] == second_a['phase'] == 'Taper przed startem A'
    assert '10 km' in first_a['focus'] and '21.1 km' in second_a['focus']
    for entry in result['entries']:
        body = entry['after']['description']
        if entry['after']['title'] == 'Bieg progowy kontrolowany':
            assert '10 min spokojnej rozgrzewki' in body
            assert 'min spokojnego schłodzenia' in body


def test_race_notes_cannot_change_classification(setup):
    svc, sheet, _ = setup
    sheet.calendar['rows'][0].update(name='Forest Run', notes='Odpoczynek przed startem; easy dojazd.')
    result = preview(svc, replace_existing=True)
    race = next(e for e in result['entries'] if e['after']['date'] == '2026-12-13')
    assert RacePlanEngine._type(race['after']) == 'race'
