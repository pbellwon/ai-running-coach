from dataclasses import dataclass
from datetime import date, timedelta
from types import SimpleNamespace

from app.services.coach_chat_context_service import CoachChatContextService
from app.services.current_goal_service import CurrentGoalService


@dataclass
class BaseContext:
    goal: str = '38:30'


def week(day):
    return {'week_start': day.isoformat(), 'week_end': (day+timedelta(days=6)).isoformat(),
            'period_status': 'completed', 'summary': {'count': 7}, 'coach': {'summary': 'Ocena tygodnia'},
            'recovery': {'available_days': 0, 'fatigue_signal': 'insufficient_data', 'average_sleep_hours': None},
            'days': [{'date': (day+timedelta(days=i)).isoformat(), 'executed_sessions': []} for i in range(7)]}


def context(weekly=None, base=None, workout=None):
    class Weekly:
        def build(self, day): return week(day)
    class Plan:
        def planned_between(self, start, end): return []
    return CoachChatContextService(
        base=base or SimpleNamespace(current_goal_service=CurrentGoalService(), build=lambda day: BaseContext()),
        weekly=weekly or Weekly(), plan=Plan(), workout=workout,
        today=lambda: date(2026, 10, 31))


def test_context_has_28_day_bound_and_explicit_selected_historical_week():
    result = context().build({'kind': 'week', 'week_start': '2026-08-03'})
    history = [v for k,v in result['facts'].items() if k.startswith('history_')]
    assert min(d['date'] for w in history for d in w['sessions']) == '2026-10-04'
    assert 'summary' not in history[0]  # Full-week aggregate includes out-of-window days.
    assert result['facts']['goal']['target_time_sec'] == 2310
    assert result['facts']['selected_week']['week_start'] == '2026-08-03'
    assert any(s.get('week_start') == '2026-08-03' for s in result['sources'])


def test_missing_services_are_limitations_and_do_not_become_healthy_evidence():
    class BrokenWeekly:
        def build(self, day): raise RuntimeError('PRIVATE UPSTREAM ERROR')
    base = SimpleNamespace(current_goal_service=CurrentGoalService(), build=lambda day: (_ for _ in ()).throw(ValueError('PRIVATE')))
    result = context(weekly=BrokenWeekly(), base=base).build({'kind': 'today'})
    assert result['facts']['goal']['distance_km'] == 10
    assert 'athlete' not in result['facts']
    assert not any(k.startswith('history_') for k in result['facts'])
    assert result['limitations']
    assert 'PRIVATE' not in str(result)
    assert not any(s['label'] == 'Historia treningów' for s in result['sources'])


def test_specific_workout_is_looked_up_by_id_and_date():
    seen = []
    class Workout:
        def build(self, session_id, target_date):
            seen.append((session_id, target_date))
            return BaseContext('Trening progowy')
    result = context(workout=Workout()).build({'kind': 'workout', 'session_id': 'session-12', 'date': '2026-10-21'})
    assert seen == [('session-12', '2026-10-21')]
    assert result['facts']['selected_workout']['goal'] == 'Trening progowy'
    assert result['sources'][-1]['session_id'] == 'session-12'


def test_context_includes_real_weekly_engine_output_from_database(monkeypatch):
    from datetime import datetime
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.database import Base
    from app.db.models import WorkoutDB
    from app.services.weekly_review_service import WeeklyReviewService
    from app.services.weekly_coach_review_service import WeeklyCoachReviewService
    import app.services.recovery_snapshot_service as snapshots

    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(snapshots, 'SessionLocal', factory)
    class EmptyPlan:
        def fetch_rows(self): return []
    weekly = WeeklyCoachReviewService(
        weekly_service=WeeklyReviewService(session_factory=factory, plan_source=EmptyPlan()),
        today=lambda: date(2026, 10, 31))
    try:
        with factory() as db:
            db.add(WorkoutDB(source_file='chat-running.fit', start_time=datetime(2026,10,26,8),
                             sport='running', distance_km=8, duration_sec=2700,
                             declared_workout_type='easy_run'))
            db.commit()
        result = context(weekly=weekly).build({'kind': 'today'})
        actual_week = result['facts']['history_2026-10-26']
        assert actual_week['summary']['executed_sessions_count'] == 1
        assert actual_week['sessions'][0]['sessions'][0]['total_distance_km'] == 8
        assert actual_week['recovery']['fatigue_signal'] == 'insufficient_data'
    finally:
        engine.dispose()
