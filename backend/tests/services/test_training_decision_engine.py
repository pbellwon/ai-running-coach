from datetime import date

from app.models.recovery_snapshot import (
    RecoveryMetric,
    RecoverySnapshot,
)
from app.models.recovery_trend import (
    MetricTrend,
    RecoveryTrend,
)
from app.models.training_context import (
    TrainingContext,
)
from app.services.training_decision_engine import (
    TrainingDecisionEngine,
)


def make_metric(
    status: str = "normal",
    current: float = 60,
) -> RecoveryMetric:
    return RecoveryMetric(
        current=current,
        baseline=60,
        difference=0,
        difference_percent=0,
        status=status,
        sample_size=10,
    )


def make_recovery(
    overall_status: str = "good",
    available_metrics_count: int = 4,
) -> RecoverySnapshot:
    return RecoverySnapshot(
        date=date(2026, 8, 1),
        hrv=make_metric(),
        resting_hr=make_metric(),
        sleep_duration=make_metric(),
        sleep_score=make_metric(),
        ctl=35,
        atl=35,
        form=0,
        overall_status=overall_status,
        warning_count=0,
        available_metrics_count=(
            available_metrics_count
        ),
        reasons=[],
    )


def make_trend(
    fatigue_signal: str = "none",
    available_days: int = 5,
    window_days: int = 5,
) -> RecoveryTrend:
    metric = MetricTrend(
        values=[
            60,
            60,
            60,
            60,
            60,
        ],
        direction="stable",
        valid_samples=5,
    )

    return RecoveryTrend(
        target_date=date(2026, 8, 1),
        window_days=window_days,
        available_days=available_days,
        hrv=metric,
        resting_hr=metric,
        sleep_duration=metric,
        sleep_score=metric,
        caution_days=0,
        poor_days=0,
        fatigue_signal=fatigue_signal,
        fatigue_score=0,
        reasons=[],
    )


def make_context(
    recent_quality: int = 0,
    recent_strength: int = 0,
) -> TrainingContext:
    return TrainingContext(
        target_date=date(2026, 8, 1),
        window_days=7,
        source_activities_count=0,
        logical_sessions_count=0,
        total_training_min=0,
        running_distance_km=0,
        running_duration_min=0,
        running_sessions=0,
        easy_sessions=0,
        quality_sessions=0,
        long_run_sessions=0,
        strength_sessions=0,
        cycling_sessions=0,
        other_sessions=0,
        recent_48h_sessions=0,
        recent_48h_training_min=0,
        recent_48h_quality_sessions=(
            recent_quality
        ),
        recent_48h_strength_sessions=(
            recent_strength
        ),
        type_counts={},
        last_session=None,
    )


def test_good_recovery_quality_day_runs_as_planned():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("good"),
        trend=make_trend("none"),
        training_context=make_context(),
        planned_workout_type="threshold",
    )

    assert result.decision == "do_as_planned"


def test_poor_recovery_and_high_fatigue_means_rest():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("poor"),
        trend=make_trend("high"),
        training_context=make_context(),
        planned_workout_type="threshold",
    )

    assert result.decision == "rest"


def test_poor_recovery_quality_day_means_easy_only():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("poor"),
        trend=make_trend("watch"),
        training_context=make_context(),
        planned_workout_type="threshold",
    )

    assert result.decision == "easy_only"


def test_accumulating_fatigue_quality_day_is_reduced():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("good"),
        trend=make_trend("accumulating"),
        training_context=make_context(),
        planned_workout_type="threshold",
    )

    assert result.decision == "reduce"


def test_caution_quality_day_is_reduced():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("caution"),
        trend=make_trend("none"),
        training_context=make_context(),
        planned_workout_type="vo2max",
    )

    assert result.decision == "reduce"


def test_recent_quality_before_quality_day_is_reduced():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("good"),
        trend=make_trend("none"),
        training_context=make_context(
            recent_quality=1
        ),
        planned_workout_type="threshold",
    )

    assert result.decision == "reduce"


def test_poor_recovery_easy_day_is_reduced():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery("poor"),
        trend=make_trend("watch"),
        training_context=make_context(),
        planned_workout_type="easy_run",
    )

    assert result.decision == "reduce"


def test_missing_data_reduces_confidence():
    result = TrainingDecisionEngine().decide(
        recovery=make_recovery(
            overall_status="insufficient_data",
            available_metrics_count=2,
        ),
        trend=make_trend(
            fatigue_signal="insufficient_data",
            available_days=2,
            window_days=5,
        ),
        training_context=make_context(),
        planned_workout_type="easy_run",
    )

    assert result.confidence < 1.0