from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import WorkoutDB
from app.services.athlete_history_service import AthleteHistoryService


def test_archive_covers_old_history_but_does_not_treat_old_or_unmarked_runs_as_current_race_proof():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        for name, when, km, seconds, kind in [
            ('old-result', datetime(2021, 6, 1, 9), 10, 2300, 'race'),
            ('new-warmup', datetime(2026, 10, 1, 8), 2, 700, 'easy_run'),
            ('new-result', datetime(2026, 10, 1, 8, 20), 10, 2400, 'race'),
            ('new-cooldown', datetime(2026, 10, 1, 9), 2, 700, 'easy_run'),
            ('fast-training', datetime(2026, 10, 8, 9), 10, 2200, 'threshold'),
            ('bad-record', datetime(2026, 9, 1, 9), 10, -100, 'race'),
            ('future', datetime(2027, 1, 1, 9), 10, 2000, 'race'),
        ]:
            db.add(WorkoutDB(source_file=name, start_time=when, sport='running',
                distance_km=km, duration_sec=seconds, declared_workout_type=kind, activity_name=name))
        db.commit()
    archive = AthleteHistoryService(factory).build(date(2026, 11, 1))
    assert archive['coverage_start'] == '2021-06-01'
    assert archive['coverage_end'] == '2026-10-08'
    assert archive['source_activities_count'] == 6
    assert archive['invalid_activities_count'] == 1
    assert [month['month'] for month in archive['months']] == ['2021-06', '2026-10']
    assert archive['months'][1]['running_km'] == 24
    assert archive['logical_sessions_count'] < archive['source_activities_count'] - archive['invalid_activities_count']
    assert archive['race_activities_count'] == 2
    races = archive['race_results']
    assert [r['recorded_duration_sec'] for r in races] == [2300, 2400]
    assert races[0]['days_ago'] > 1000
    assert all(r['distance_km'] == 10 and 'not_verified' in r['time_basis'] for r in races)
    engine.dispose()


def test_empty_archive_is_explicit_and_does_not_invent_performance():
    engine = create_engine('sqlite://', poolclass=StaticPool)
    Base.metadata.create_all(engine)
    archive = AthleteHistoryService(sessionmaker(bind=engine)).build(date(2026, 11, 1))
    assert archive['coverage_start'] is None
    assert archive['logical_sessions_count'] == 0
    assert archive['months'] == archive['race_results'] == []
    assert archive['limitations']
    engine.dispose()
