from app.models.training_decision import TrainingDecision
from app.services.today_recommendation_service import (
    TodayRecommendationService,
)


def make_decision(
    decision: str,
    planned_workout_type: str = "threshold",
) -> TrainingDecision:
    return TrainingDecision(
        decision=decision,
        confidence=1.0,
        recovery_status="good",
        fatigue_signal="none",
        planned_workout_type=planned_workout_type,
        planned_session_role=None,
        reasons=["Test reason."],
        warnings=["Test warning."],
    )


def test_do_as_planned_keeps_original_workout():
    result = TodayRecommendationService().build(
        decision=make_decision("do_as_planned"),
        planned_title="3x3km threshold",
        planned_workout_type="threshold",
        planned_distance_km=14.0,
        planned_duration_min=70,
    )

    assert result.recommendation_type == "as_planned"
    assert result.recommended_workout_type == "threshold"
    assert result.recommended_distance_km == 14.0
    assert result.recommended_duration_min == 70


def test_reduce_keeps_type_and_reduces_volume():
    result = TodayRecommendationService().build(
        decision=make_decision("reduce"),
        planned_title="3x3km threshold",
        planned_workout_type="threshold",
        planned_distance_km=14.0,
        planned_duration_min=70,
    )

    assert result.recommendation_type == "reduced"
    assert result.recommended_workout_type == "threshold"
    assert result.recommended_distance_km == 9.8
    assert result.recommended_duration_min == 49


def test_easy_only_replaces_quality_with_easy_run():
    result = TodayRecommendationService().build(
        decision=make_decision("easy_only"),
        planned_title="3x3km threshold",
        planned_workout_type="threshold",
        planned_distance_km=14.0,
        planned_duration_min=70,
    )

    assert result.recommendation_type == "easy_replacement"
    assert result.original_workout_type == "threshold"
    assert result.recommended_workout_type == "easy_run"
    assert result.recommended_distance_km == 9.8
    assert result.recommended_duration_min == 49


def test_rest_removes_training():
    result = TodayRecommendationService().build(
        decision=make_decision("rest"),
        planned_title="3x3km threshold",
        planned_workout_type="threshold",
        planned_distance_km=14.0,
        planned_duration_min=70,
    )

    assert result.recommendation_type == "rest"
    assert result.recommended_workout_type is None
    assert result.recommended_distance_km == 0.0
    assert result.recommended_duration_min == 0