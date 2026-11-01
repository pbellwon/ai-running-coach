from copy import deepcopy
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.services.plan_correction_service import PlanCorrectionService
from app.services.coach_chat_service import ChatError
from app.api import plan_corrections
from app.main import app
from app.integrations.google_sheets_plan_source import GoogleSheetsPlanSource

class Sheet:
    def __init__(self):
        self.snapshot = {'source': ['test', '1'], 'headers': ['date', 'title', 'description', 'planned_distance_km', 'planned_duration_min', 'priority', 'uwagi'], 'rows': [
            {'date': '2026-11-02', 'title': 'Threshold', 'description': '3 x 10 min\nUwagi trenera: ostrożnie.\nPaceMind stara notka', 'planned_distance_km': '10', 'planned_duration_min': '60', 'priority': 'high', 'uwagi': '=literal'}]}
        self.writes = 0
        self.failure = None
    def correction_snapshot(self):
        return deepcopy(self.snapshot)
    def write_correction(self, snapshot, row, before, after):
        self.writes += 1
        if self.failure == 'before':
            raise TimeoutError()
        self.snapshot['rows'][row - 2] = deepcopy(after)
        if self.failure == 'after':
            raise TimeoutError()

@pytest.fixture
def setup():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sheet = Sheet()
    svc = PlanCorrectionService(sheet, factory, now=lambda: datetime(2026, 11, 1, 12))
    yield svc, sheet, factory
    engine.dispose()

def preview(svc, identifier=None):
    return svc.preview(identifier or str(uuid4()), svc.plan()['version'], 2,
        {'title': 'Spokojny bieg', 'planned_distance_km': 7.0, 'planned_duration_min': 42, 'description': '7 km spokojnie, bez akcentów.'}, 'Zmęczenie po ostatnich sesjach.')

def test_preview_requires_acceptance_and_preserves_notes(setup):
    svc, sheet, _ = setup
    item = preview(svc)
    assert sheet.writes == 0
    assert item['after']['description'].startswith(item['before']['description'])
    assert item['after']['description'].endswith('Uzasadnienie: Zmęczenie po ostatnich sesjach.')
    assert 'PaceMind 2026-11-01' in item['after']['description']
    assert item['after']['uwagi'] == '=literal'
    applied = svc.decide(item['id'], True)
    assert applied['status'] == 'applied'
    assert svc.decide(item['id'], True) == applied
    assert sheet.writes == 1
    assert svc.history()['items'][0]['before'] == item['before']

@pytest.mark.parametrize('where', ['title', 'description', 'uwagi'])
def test_stale_plan_never_writes(setup, where):
    svc, sheet, _ = setup
    item = preview(svc)
    sheet.snapshot['rows'][0][where] += ' changed'
    with pytest.raises(ChatError, match='Plan zmienił'):
        svc.decide(item['id'], True)
    assert sheet.writes == 0
    assert svc.history()['items'][0]['status'] == 'stale'

def test_rejection_and_conflicting_decision(setup):
    svc, sheet, _ = setup
    item = preview(svc)
    assert svc.decide(item['id'], False)['status'] == 'rejected'
    assert svc.decide(item['id'], False)['status'] == 'rejected'
    with pytest.raises(ChatError):
        svc.decide(item['id'], True)
    assert sheet.writes == 0

def test_lost_response_reconciles_without_duplicate(setup):
    svc, sheet, _ = setup
    sheet.failure = 'after'
    item = preview(svc)
    assert svc.decide(item['id'], True)['status'] == 'applied'
    assert svc.decide(item['id'], True)['status'] == 'applied'
    assert sheet.writes == 1

def test_ambiguous_failure_blocks_new_writers_even_after_restart(setup):
    svc, sheet, factory = setup
    first, second = preview(svc), preview(svc)
    sheet.failure = 'before'
    with pytest.raises(ChatError, match='nie jest potwierdzony'):
        svc.decide(first['id'], True)
    restarted = PlanCorrectionService(sheet, factory, now=svc.now)
    with pytest.raises(ChatError):
        restarted.decide(first['id'], True)
    with pytest.raises(ChatError, match='Inny zapis'):
        restarted.decide(second['id'], True)
    assert sheet.writes == 1

def test_preview_idempotent_and_conflicting_payload(setup):
    svc, sheet, _ = setup
    identifier = str(uuid4())
    first = preview(svc, identifier)
    assert preview(svc, identifier) == first
    with pytest.raises(ChatError):
        svc.preview(identifier, first['version'], 2, {}, 'Different')

def test_second_correction_retains_original_and_history(setup):
    svc, sheet, _ = setup
    first = preview(svc)
    svc.decide(first['id'], True)
    second = preview(svc)
    svc.decide(second['id'], True)
    assert len(svc.history()['items']) == 2
    assert second['after']['description'].startswith(first['after']['description'])
    assert first['before']['description'] in second['after']['description']

def test_expired_date(setup):
    svc, sheet, _ = setup
    item = preview(svc)
    svc.now = lambda: datetime(2026, 11, 3)
    with pytest.raises(ChatError):
        svc.decide(item['id'], True)
    assert sheet.writes == 0

def test_api_auth_validation_and_acceptance(setup, monkeypatch):
    svc, sheet, _ = setup
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', 'test-owner-code-12345678')
    app.dependency_overrides[plan_corrections.service] = lambda: svc
    try:
        client = TestClient(app)
        assert client.get('/coach/corrections/plan').status_code == 401
        headers = {'Authorization': 'Bearer test-owner-code-12345678'}
        assert client.get('/coach/corrections/plan', headers=headers).status_code == 200
        invalid = {'id': str(uuid4()), 'version': svc.plan()['version'], 'row': 2, 'change': {'title': ' ', 'description': 'x', 'planned_distance_km': -1}, 'reason': 'x'}
        assert client.post('/coach/corrections/preview', json=invalid, headers=headers).status_code == 422
        item = preview(svc)
        response = client.post(f"/coach/corrections/{item['id']}/decision", json={'decision': 'accept'}, headers=headers)
        assert response.status_code == 200
        assert response.json()['status'] == 'applied'
    finally:
        app.dependency_overrides.pop(plan_corrections.service)

def test_sheets_writer_uses_raw_changed_cells_only():
    source = GoogleSheetsPlanSource('test', 'plan', 'unused')
    sheet = Mock(id=1)
    source._correction_worksheet = lambda: sheet
    before = {'title': 'Old', 'description': 'Original', 'uwagi': 'untouched'}
    after = before | {'description': '=not a formula'}
    source.write_correction({'source': ['test', '1'], 'headers': list(before)}, 4, before, after)
    sheet.batch_update.assert_called_once_with([{'range': 'B4', 'values': [['=not a formula']]}], value_input_option='RAW')

def test_old_intervals_do_not_drive_accepted_easy_workout(setup):
    from app.engine.existing_plan_importer import ExistingPlanImporter
    svc, sheet, _ = setup
    item = preview(svc)
    svc.decide(item['id'], True)
    workout = ExistingPlanImporter().import_rows(sheet.snapshot['rows'])[0]
    assert workout.workout_type == 'easy_run'
    assert workout.structure == []
    assert '3 x 10 min' in workout.description


def test_global_gate_blocks_overlapping_write_and_old_preview(setup):
    svc, sheet, _ = setup
    first, second = preview(svc), preview(svc)
    original_write = sheet.write_correction
    def overlapping(*args):
        with pytest.raises(ChatError, match='Inny zapis'):
            svc.decide(second['id'], True)
        original_write(*args)
    sheet.write_correction = overlapping
    svc.decide(first['id'], True)
    with pytest.raises(ChatError, match='Plan zmienił'):
        svc.decide(second['id'], True)
    assert sheet.writes == 1
