from datetime import date

from app.models.planned_workout import PlannedWorkout
from app.models.training_decision import TrainingDecision
from app.models.today_recommendation import TodayRecommendation
from app.services.adaptive_planning_service import AdaptivePlanningService


class StubPlanSource:
    def fetch_rows(self):
        return [{}]


class StubPlanImporter:
    def __init__(self, workout):
        self.workout = workout

    def import_rows(self, rows):
        return [self.workout]


class StubBuildService:
    def __init__(self, result):
        self.result = result

    def build(self, target_date):
        return self.result


class StubTrainingDecisionEngine:
    def __init__(self, result):
        self.result = result

    def decide(self, **kwargs):
        return self.result


class StubRecommendationService:
    def __init__(self, result):
        self.result = result

    def build(self, **kwargs):
        return self.result


class StubRecentReviewService:
    def __init__(self, result):
        self.result = result

    def build(self, **kwargs):
        return self.result


def make_workout():
    return PlannedWorkout(
        planned_date=date(2026, 10, 13),
        title="Threshold 3 x 10 min",
        description="Controlled threshold session",
        workout_type="threshold",
        intent=None,
        planned_distance_km=13.0,
        planned_duration_min=70,
        structure=[],
        priority="high",
    )


def make_training_decision(decision="do_as_planned"):
    return TrainingDecision(
        decision=decision,
        confidence=0.9,
        recovery_status="good",
        fatigue_signal="low",
        planned_workout_type="threshold",
        planned_session_role=None,
        reasons=["No strong recovery or fatigue signal requires a training change."],
        warnings=[],
    )


def make_recommendation(
    recommendation_type="as_planned",
    workout_type="threshold",
    distance_km=13.0,
    duration_min=70,
):
    return TodayRecommendation(
        decision="do_as_planned",
        recommendation_type=recommendation_type,
        original_workout_type="threshold",
        recommended_workout_type=workout_type,
        original_distance_km=13.0,
        recommended_distance_km=distance_km,
        original_duration_min=70,
        recommended_duration_min=duration_min,
        title="Threshold 3 x 10 min",
        summary="Complete the planned workout as scheduled.",
        reasons=[],
        warnings=[],
    )


def make_service(
    recommendation=None,
    recent_reviews=None,
):
    workout = make_workout()

    return AdaptivePlanningService(
        plan_source=StubPlanSource(),
        plan_importer=StubPlanImporter(workout),
        recovery_service=StubBuildService(object()),
        recovery_trend_service=StubBuildService(object()),
        training_context_service=StubBuildService(object()),
        training_decision_engine=StubTrainingDecisionEngine(
            make_training_decision()
        ),
        recommendation_service=StubRecommendationService(
            recommendation or make_recommendation()
        ),
        recent_review_service=StubRecentReviewService(
            recent_reviews or []
        ),
    )


def test_keep_plan_proposal():
    proposal = make_service().build("2026-10-13")

    assert proposal is not None
    assert proposal.decision == "keep_plan"
    assert proposal.proposed_workout_type == "threshold"
    assert proposal.proposed_distance_km == 13.0
    assert proposal.proposed_duration_min == 70


def test_reduced_recommendation_maps_to_reduce_load():
    recommendation = make_recommendation(
        recommendation_type="reduced",
        workout_type="threshold",
        distance_km=9.1,
        duration_min=49,
    )

    proposal = make_service(
        recommendation=recommendation
    ).build("2026-10-13")

    assert proposal.decision == "reduce_load"
    assert proposal.proposed_distance_km == 9.1
    assert proposal.proposed_duration_min == 49


def test_repeated_too_hard_sessions_trigger_manual_review():
    recent_reviews = [
        {
            "date": "2026-10-12",
            "review": {
                "status": "too_hard",
                "confidence": 0.9,
            },
        },
        {
            "date": "2026-10-10",
            "review": {
                "status": "too_hard",
                "confidence": 0.8,
            },
        },
        {
            "date": "2026-10-08",
            "review": {
                "status": "on_target",
                "confidence": 0.9,
            },
        },
    ]

    proposal = make_service(
        recent_reviews=recent_reviews
    ).build("2026-10-13")

    assert proposal.decision == "manual_review"
    assert proposal.proposed_workout_type == "threshold"
    assert proposal.proposed_distance_km == 13.0


def test_no_planned_workout_returns_none():
    service = AdaptivePlanningService(
        plan_source=StubPlanSource(),
        plan_importer=StubPlanImporter(None),
        recovery_service=StubBuildService(object()),
        recovery_trend_service=StubBuildService(object()),
        training_context_service=StubBuildService(object()),
        training_decision_engine=StubTrainingDecisionEngine(
            make_training_decision()
        ),
        recommendation_service=StubRecommendationService(
            make_recommendation()
        ),
        recent_review_service=StubRecentReviewService([]),
    )

    service.plan_importer.import_rows = lambda rows: []

    proposal = service.build("2026-10-13")

    assert proposal is None