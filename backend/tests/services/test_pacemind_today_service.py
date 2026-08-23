from datetime import date

from app.models.planned_workout import PlannedWorkout
from app.services.pacemind_today_service import PaceMindTodayService


def make_planned_workout() -> PlannedWorkout:
    return PlannedWorkout(
        planned_date=date(2026, 8, 1),
        title="easy + strides",
        description="9km easy + 6x100",
        workout_type="easy_run+strides",
        intent=None,
        planned_distance_km=9.0,
        planned_duration_min=None,
        structure=[],
        priority="normal",
    )


def test_no_planned_workout_returns_no_plan_status(monkeypatch):
    service = PaceMindTodayService()

    monkeypatch.setattr(
        service,
        "_get_planned_workout",
        lambda target_date: None,
    )

    result = service.build("2026-08-01")

    assert result.status == "no_planned_workout"
    assert result.planned_workout is None
    assert result.recovery is None
    assert result.decision is None
    assert result.recommendation is None


def test_planned_workout_is_loaded(monkeypatch):
    service = PaceMindTodayService()

    planned = make_planned_workout()

    monkeypatch.setattr(
        service,
        "_get_planned_workout",
        lambda target_date: planned,
    )

    class FakeRecoveryService:
        def build(self, target_date):
            return "recovery"

    class FakeTrendService:
        def build(self, target_date):
            return "trend"

    class FakeContextService:
        def build(self, target_date):
            return "context"

    class FakeDecisionEngine:
        def decide(
            self,
            recovery,
            trend,
            training_context,
            planned_workout_type,
            planned_session_role,
        ):
            return "decision"

    class FakeRecommendationService:
        def build(
            self,
            decision,
            planned_title,
            planned_workout_type,
            planned_distance_km,
            planned_duration_min,
        ):
            return "recommendation"

    monkeypatch.setattr(
        "app.services.pacemind_today_service.RecoverySnapshotService",
        FakeRecoveryService,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.RecoveryTrendService",
        FakeTrendService,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.TrainingContextService",
        FakeContextService,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.TrainingDecisionEngine",
        FakeDecisionEngine,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.TodayRecommendationService",
        FakeRecommendationService,
    )

    result = service.build("2026-08-01")

    assert result.status == "ready"

    assert result.planned_workout.title == "easy + strides"
    assert (
        result.planned_workout.workout_type
        == "easy_run+strides"
    )

    assert result.recovery == "recovery"
    assert result.recovery_trend == "trend"
    assert result.training_context == "context"
    assert result.decision == "decision"
    assert result.recommendation == "recommendation"


def test_long_run_sets_long_run_session_role(monkeypatch):
    service = PaceMindTodayService()

    planned = make_planned_workout()
    planned.workout_type = "long_run"

    monkeypatch.setattr(
        service,
        "_get_planned_workout",
        lambda target_date: planned,
    )

    captured = {}

    class FakeRecoveryService:
        def build(self, target_date):
            return "recovery"

    class FakeTrendService:
        def build(self, target_date):
            return "trend"

    class FakeContextService:
        def build(self, target_date):
            return "context"

    class FakeDecisionEngine:
        def decide(
            self,
            recovery,
            trend,
            training_context,
            planned_workout_type,
            planned_session_role,
        ):
            captured["session_role"] = planned_session_role
            return "decision"

    class FakeRecommendationService:
        def build(
            self,
            decision,
            planned_title,
            planned_workout_type,
            planned_distance_km,
            planned_duration_min,
        ):
            return "recommendation"

    monkeypatch.setattr(
        "app.services.pacemind_today_service.RecoverySnapshotService",
        FakeRecoveryService,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.RecoveryTrendService",
        FakeTrendService,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.TrainingContextService",
        FakeContextService,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.TrainingDecisionEngine",
        FakeDecisionEngine,
    )

    monkeypatch.setattr(
        "app.services.pacemind_today_service.TodayRecommendationService",
        FakeRecommendationService,
    )

    service.build("2026-08-01")

    assert captured["session_role"] == "long_run"