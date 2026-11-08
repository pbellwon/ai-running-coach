from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db.database import Base
from app.db.models import WorkoutDB
from app.services import training_context_service


@pytest.fixture
def client(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(training_context_service, 'SessionLocal', factory)
    with factory() as db:
        # Both inclusive boundaries, the day outside each window, and tomorrow.
        for offset in (0, 6, 7, 27, 28, -1):
            day = date(2026, 10, 29) - timedelta(days=offset)
            db.add(WorkoutDB(source_file=f'overview-{offset}.fit',
                start_time=datetime.combine(day, datetime.min.time()) + timedelta(hours=8),
                sport='running', declared_workout_type='easy_run',
                distance_km=8, duration_sec=45 * 60))
        db.commit()
    with TestClient(main.app) as test_client:
        yield test_client
    engine.dispose()


@pytest.mark.parametrize('days,expected', [(7, 2), (28, 4)])
def test_rolling_windows_include_today_and_exclude_outside_days(client, days, expected):
    response = client.get(f'/training/overview?target_date=2026-10-29&window_days={days}')
    assert response.status_code == 200
    summary = response.json()
    assert summary['window_days'] == days
    assert summary['target_date'] == '2026-10-29'
    assert summary['logical_sessions_count'] == expected
    assert summary['running_sessions'] == expected
    assert summary['running_distance_km'] == expected * 8
    assert summary['total_training_min'] == expected * 45


def test_default_keeps_existing_28_day_contract(client):
    response = client.get('/training/overview?target_date=2026-10-29')
    assert response.status_code == 200
    assert response.json()['window_days'] == 28
    assert response.json()['running_sessions'] == 4


@pytest.mark.parametrize('query', ['window_days=0', 'window_days=14', 'window_days=abc', 'target_date=invalid'])
def test_invalid_queries_are_rejected_before_reading_data(client, monkeypatch, query):
    def unexpected(*args, **kwargs):
        raise AssertionError('Invalid request must not read training history')
    monkeypatch.setattr(training_context_service.TrainingContextService, 'build', unexpected)
    assert client.get(f'/training/overview?{query}').status_code == 422
