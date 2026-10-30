from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import WorkoutDB, DailyAthleteStateDB
from app.models.planned_workout import PlannedWorkout
from app.services.composite_session_builder import CompositeSessionBuilder
from app.services.recent_execution_review_service import RecentExecutionReviewService
from app.services.weekly_review_service import WeeklyReviewService
from app.services.weekly_coach_review_service import WeeklyCoachReviewService
from app.services.recovery_snapshot_service import RecoverySnapshotService
from app.services.workout_feedback_service import WorkoutFeedbackService

MONDAY = date(2026, 10, 19)
TODAY = date(2026, 10, 29)


class DeclaredResolver:
    def resolve(self, workout):
        return {"workout_type": workout.declared_workout_type or "unknown",
                "confidence": 0.9 if workout.declared_workout_type else 0.2,
                "classification_method": "test_declared", "warnings": []}


class EmptyStructure:
    def analyze(self, filename):
        return {"segments": [], "summary": {"warnings": []}}


@pytest.fixture
def weekly_setup(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    plans = []

    class PlanSource:
        def fetch_rows(self):
            return plans

    class Importer:
        def import_rows(self, rows):
            return rows

    import app.services.recovery_snapshot_service as snapshot_module
    monkeypatch.setattr(snapshot_module, "SessionLocal", factory)
    reviewer = RecentExecutionReviewService(session_factory=factory, structure_analyzer=EmptyStructure())
    weekly = WeeklyReviewService(
        session_factory=factory, plan_source=PlanSource(), plan_importer=Importer(),
        session_builder=CompositeSessionBuilder(resolver=DeclaredResolver()),
        execution_review_service=reviewer,
    )
    service = WeeklyCoachReviewService(weekly_service=weekly, today=lambda: TODAY)
    yield service, plans, factory
    engine.dispose()


def add_plan(plans, day=MONDAY, kind="easy_run", distance=8, duration=45, title="Easy"):
    plans.append(PlannedWorkout(
        planned_date=day, title=title, description=title, workout_type=kind,
        intent=None, planned_distance_km=distance, planned_duration_min=duration,
        structure=[], priority="normal",
    ))


def add_workout(factory, day=MONDAY, kind="easy_run", distance=8, duration=45, hour=8, filename=None):
    with factory() as db:
        db.add(WorkoutDB(
            source_file=filename or f"{day}-{kind}-{hour}.fit",
            start_time=datetime.combine(day, datetime.min.time()) + timedelta(hours=hour),
            sport="running" if kind != "strength" else "training",
            duration_sec=duration * 60, distance_km=distance, declared_workout_type=kind,
        ))
        db.commit()


def add_recovery(factory, poor=False):
    with factory() as db:
        for offset in range(-15, 7):
            day = MONDAY + timedelta(days=offset)
            affected = poor and offset >= 2
            db.add(DailyAthleteStateDB(
                date=datetime.combine(day, datetime.min.time()),
                hrv=25 if affected else 60, resting_hr=65 if affected else 48,
                sleep_sec=4 * 3600 if affected else 8 * 3600,
                sleep_score=40 if affected else 85, ctl=40, atl=65 if affected else 40,
            ))
        db.commit()


def test_defaults_to_last_complete_week_and_reviews_every_session(weekly_setup):
    service, plans, factory = weekly_setup
    for offset in range(7):
        day = MONDAY + timedelta(days=offset)
        add_plan(plans, day)
        add_workout(factory, day)
    add_workout(factory, MONDAY - timedelta(days=1))
    add_workout(factory, MONDAY + timedelta(days=7))
    add_recovery(factory)
    result = service.build()
    assert result["week_start"] == "2026-10-19"
    assert result["week_end"] == "2026-10-25"
    assert result["period_status"] == "completed"
    assert result["summary"]["executed_sessions_count"] == 7
    assert result["coach"]["execution_assessments"]["on_target"] == 7
    assert result["recovery"]["available_days"] == 7
    assert result["recovery"]["fatigue_signal"] == "none"
    assert result["coach"]["verdict"] == "on_track"
    assert len(result["days"]) == 7


def test_empty_week_is_honest_about_missing_data(weekly_setup):
    service, _, _ = weekly_setup
    result = service.build()
    assert result["status"] == "no_execution_data"
    assert result["coach"]["verdict"] == "insufficient_data"
    assert not result["coach"]["positives"]
    assert result["recovery"]["available_days"] == 0
    assert result["recovery"]["missing_days"] == 7
    assert result["recovery"]["fatigue_signal"] == "insufficient_data"
    assert result["recovery"]["average_sleep_hours"] is None
    assert not result["summary"]["planned_distance_complete"]


def test_current_and_future_days_are_pending_not_missed(weekly_setup):
    service, plans, factory = weekly_setup
    monday = date(2026, 10, 26)
    for offset in range(7):
        add_plan(plans, monday + timedelta(days=offset))
    add_workout(factory, date(2026, 10, 31))
    result = service.build(monday)
    assert result["period_status"] == "in_progress"
    assert result["as_of_date"] == "2026-10-29"
    assert result["summary"]["missed_workouts_count"] == 3
    assert result["summary"]["pending_workouts_count"] == 4
    assert result["summary"]["executed_sessions_count"] == 0
    assert result["recovery"]["missing_days"] == 4
    assert all(day["planned_workouts"][0]["match_status"] == "pending" for day in result["days"][3:])


def test_one_to_one_matching_is_shared_with_assessments(weekly_setup):
    service, plans, factory = weekly_setup
    add_plan(plans)
    add_workout(factory, hour=8)
    add_workout(factory, hour=18)
    result = service.build()
    sessions = result["days"][0]["executed_sessions"]
    assert result["summary"]["paired_workouts_count"] == 1
    assert result["summary"]["unplanned_workouts_count"] == 1
    assert sorted(session["execution_review"]["status"] for session in sessions) == ["insufficient_evidence", "on_target"]
    assert sum(session["execution_review"]["planned_workout_type"] is not None for session in sessions) == 1


def test_feedback_and_recovery_drive_coaching(weekly_setup):
    service, plans, factory = weekly_setup
    for offset in (0, 2):
        day = MONDAY + timedelta(days=offset)
        add_plan(plans, day)
        add_workout(factory, day)
    first = service.build()
    feedback = WorkoutFeedbackService(factory)
    for day in first["days"]:
        for session in day["executed_sessions"]:
            feedback.upsert(session["session_id"], perceived_effort=9, execution_feeling="too_hard", comment="Heavy legs")
    add_recovery(factory, poor=True)
    result = service.build()
    assert result["coach"]["execution_assessments"]["too_hard"] == 2
    assert result["coach"]["verdict"] == "caution"
    assert result["recovery"]["fatigue_signal"] in {"accumulating", "high"}
    assert {step["code"] for step in result["coach"]["next_steps"]} >= {"repeated_difficulty", "protect_recovery"}
    assert all(step["evidence"] for step in result["coach"]["next_steps"])
    assert result["days"][0]["executed_sessions"][0]["execution_review"]["athlete_feedback"]["execution_feeling"] == "too_hard"


def test_missing_baselines_are_qualified(weekly_setup):
    service, _, factory = weekly_setup
    with factory() as db:
        for offset in range(7):
            db.add(DailyAthleteStateDB(
                date=datetime.combine(MONDAY + timedelta(days=offset), datetime.min.time()),
                hrv=50, resting_hr=50,
            ))
        db.commit()
    result = service.build()
    assert result["recovery"]["missing_baseline_days"] >= 5
    assert any("bazy odniesienia" in text for text in result["coach"]["limitations"])


def test_missing_plans_do_not_produce_confident_assessments(weekly_setup):
    service, _, factory = weekly_setup
    add_workout(factory)
    result = service.build()
    assert result["status"] == "ready"
    assert result["coach"]["verdict"] == "insufficient_data"
    assert result["coach"]["execution_assessments"]["insufficient_evidence"] == 1


def test_empty_wellness_rows_are_not_recovery_evidence(weekly_setup):
    service, _, factory = weekly_setup
    with factory() as db:
        for offset in range(7):
            db.add(DailyAthleteStateDB(date=datetime.combine(MONDAY + timedelta(days=offset), datetime.min.time())))
        db.commit()
    recovery = service.build()["recovery"]
    assert recovery["available_days"] == 0
    assert recovery["fatigue_signal"] == "insufficient_data"


@pytest.mark.parametrize("week_start", ["2026-10-27", "2026-11-02", "not-a-date"])
def test_invalid_or_future_week(weekly_setup, week_start):
    service, _, _ = weekly_setup
    with pytest.raises(ValueError):
        service.build(week_start)


def test_year_boundary(weekly_setup):
    service, _, _ = weekly_setup
    service.today = lambda: date(2027, 1, 4)
    result = service.build()
    assert result["week_start"] == "2026-12-28"
    assert result["week_end"] == "2027-01-03"


def test_all_three_execution_categories_are_aggregated(weekly_setup):
    service, plans, factory = weekly_setup
    for offset, distance, duration in [(0, 8, 45), (1, 12, 70), (2, 4, 20)]:
        day = MONDAY + timedelta(days=offset)
        add_plan(plans, day)
        add_workout(factory, day, distance=distance, duration=duration)
    counts = service.build()["coach"]["execution_assessments"]
    assert counts == {"on_target": 1, "too_hard": 1, "too_easy": 1, "insufficient_evidence": 0}


def test_low_confidence_assessments_do_not_trigger_fatigue_conclusions(weekly_setup):
    service, plans, factory = weekly_setup
    for offset in (0, 2):
        day = MONDAY + timedelta(days=offset)
        add_plan(plans, day)
        add_workout(factory, day, distance=12, duration=70)
    weekly = service.weekly_service.review(MONDAY, include_execution_reviews=True)
    for day in weekly["days"]:
        for session in day["executed_sessions"]:
            session["execution_review"]["confidence"] = 0.2
    result = service.coach_engine.review(weekly, service._recovery(MONDAY, MONDAY + timedelta(days=6)))
    assert result["verdict"] == "insufficient_data"
    assert "repeated_difficulty" not in {step["code"] for step in result["next_steps"]}
    assert result["uncertain_sessions_count"] == 2


def test_incomplete_distance_plan_does_not_claim_volume_difference(weekly_setup):
    service, plans, factory = weekly_setup
    add_plan(plans, distance=None)
    add_workout(factory)
    result = service.build()
    assert not result["summary"]["planned_distance_complete"]
    assert result["summary"]["distance_difference_km"] is None


def test_wellness_calculation_errors_are_not_silently_treated_as_missing_days(weekly_setup):
    service, _, _ = weekly_setup

    class BrokenSnapshots:
        def build(self, target_date):
            raise ValueError("Unexpected calculation failure")

    service.snapshot_service = BrokenSnapshots()
    with pytest.raises(ValueError, match="Unexpected calculation failure"):
        service.build()


def test_composite_workout_is_reviewed_once_instead_of_three_times(weekly_setup):
    service, plans, factory = weekly_setup
    add_plan(plans, kind="threshold", distance=13, duration=70, title="Threshold with warm-up")
    with factory() as db:
        for minute, kind, distance, duration, name in [
            (0, "easy_run", 3, 20, "warmup"),
            (25, "threshold", 7, 35, "main"),
            (65, "easy_run", 3, 15, "cooldown"),
        ]:
            db.add(WorkoutDB(
                source_file=f"{name}.fit", start_time=datetime(2026, 10, 19, 8) + timedelta(minutes=minute),
                sport="running", distance_km=distance, duration_sec=duration * 60,
                declared_workout_type=kind,
            ))
        db.commit()
    result = service.build()
    assert result["summary"]["executed_source_activities_count"] == 3
    assert result["summary"]["executed_sessions_count"] == 1
    assert result["coach"]["execution_assessments"]["on_target"] == 1
    assert result["days"][0]["executed_sessions"][0]["activities_count"] == 3


def test_running_and_strength_same_day_keep_separate_plan_matches(weekly_setup):
    service, plans, factory = weekly_setup
    add_plan(plans)
    add_plan(plans, kind="strength", distance=None, duration=50, title="Strength")
    add_workout(factory)
    add_workout(factory, kind="strength", distance=0, duration=50, hour=18)
    result = service.build()
    sessions = result["days"][0]["executed_sessions"]
    assert result["summary"]["paired_workouts_count"] == 2
    assert {s["execution_review"]["planned_workout_type"] for s in sessions} == {"easy_run", "strength"}


def test_story_links_supported_stimulus_to_configured_goal(weekly_setup):
    service, plans, factory = weekly_setup
    add_plan(plans, kind="threshold")
    add_workout(factory, kind="threshold")
    result = service.build()
    coach = result["coach"]
    assert [benefit["code"] for benefit in coach["training_benefits"]] == ["threshold"]
    assert coach["training_benefits"][0]["evidence"]
    assert coach["goal_context"]["label"] == "10 km w 38:30"
    assert coach["goal_context"]["target_pace"] == "3:51/km"
    assert "nie prognoza" in coach["goal_context"]["limitation"]
    assert "wystarczających danych" in coach["load_interpretation"]
    assert "on_target" not in coach["summary"]


def test_story_does_not_sell_excessive_stimulus_as_progress(weekly_setup):
    service, plans, factory = weekly_setup
    add_plan(plans, kind="threshold", distance=5, duration=30)
    add_workout(factory, kind="threshold", distance=10, duration=60)
    add_recovery(factory, poor=True)
    coach = service.build()["coach"]
    assert coach["execution_assessments"]["too_hard"] == 1
    assert not coach["training_benefits"]
    assert "sygnały" in coach["load_interpretation"]
    assert "Nie ma dość" in coach["goal_context"]["summary"]


def test_empty_story_and_missing_goal_do_not_invent_progress(weekly_setup):
    service, _, _ = weekly_setup

    class NoGoal:
        def get(self):
            return None

    service.goal_service = NoGoal()
    coach = service.build()["coach"]
    assert not coach["training_benefits"]
    assert coach["goal_context"] is None
    assert "wykluczyć" in coach["load_interpretation"]
