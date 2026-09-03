from datetime import datetime, timedelta, date

from app.models.executed_session import ExecutedSession
from app.models.goal import Goal
from app.services.goal_progress_engine import (
    GoalProgressEngine,
)


def make_session(
    session_id: str,
    start_time: datetime,
    workout_type: str,
    distance_km: float,
    duration_min: float,
) -> ExecutedSession:
    return ExecutedSession(
        session_id=session_id,
        start_time=start_time,
        end_time=(
            start_time
            + timedelta(minutes=duration_min)
        ),
        sport_family="running",
        workout_type=workout_type,
        confidence=0.9,
        classification_method="test",
        components=[],
        total_distance_km=distance_km,
        total_duration_min=duration_min,
        warnings=[],
    )


def test_aerobic_base_is_improving_when_recent_volume_is_higher():
    previous_sessions = [
        make_session(
            session_id="previous-1",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=8,
            duration_min=45,
        ),
        make_session(
            session_id="previous-2",
            start_time=datetime(
                2026,
                7,
                4,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=10,
            duration_min=55,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-1",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=10,
            duration_min=55,
        ),
        make_session(
            session_id="recent-2",
            start_time=datetime(
                2026,
                8,
                1,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=14,
            duration_min=75,
        ),
        make_session(
            session_id="recent-3",
            start_time=datetime(
                2026,
                8,
                3,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=8,
            duration_min=45,
        ),
    ]

    result = GoalProgressEngine().analyze_aerobic_base(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.area == "aerobic_base"
    assert result.status == "improving"
    assert result.trend is not None
    assert result.trend > 0
    assert result.confidence > 0
    assert result.evidence

def test_aerobic_base_is_stable_when_volume_is_similar():
    previous_sessions = [
        make_session(
            session_id="previous-1",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=20,
            duration_min=110,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-1",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=21,
            duration_min=115,
        ),
    ]

    result = GoalProgressEngine().analyze_aerobic_base(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.trend is not None
    assert 0 < result.trend < 0.10


def test_aerobic_base_is_declining_when_recent_volume_is_lower():
    previous_sessions = [
        make_session(
            session_id="previous-1",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=30,
            duration_min=165,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-1",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=20,
            duration_min=110,
        ),
    ]

    result = GoalProgressEngine().analyze_aerobic_base(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "declining"
    assert result.trend is not None
    assert result.trend < -0.10

def test_aerobic_base_has_insufficient_evidence_without_previous_volume():
    recent_sessions = [
        make_session(
            session_id="recent-1",
            start_time=datetime(
                2026,
                8,
                1,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=12,
            duration_min=65,
        ),
    ]

    result = GoalProgressEngine().analyze_aerobic_base(
        recent_sessions=recent_sessions,
        previous_sessions=[],
    )

    assert result.area == "aerobic_base"
    assert result.status == "insufficient_evidence"
    assert result.trend is None
    assert result.confidence == 0.3
    assert result.evidence

def test_long_run_durability_is_improving_when_recent_long_run_is_bigger():
    previous_sessions = [
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=15,
            duration_min=85,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=18,
            duration_min=100,
        ),
    ]

    result = GoalProgressEngine().analyze_long_run_durability(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.area == "long_run_durability"
    assert result.status == "improving"
    assert result.trend is not None
    assert result.trend > 0
    assert result.confidence > 0
    assert result.evidence

def test_long_run_durability_is_stable_when_longest_run_is_similar():
    previous_sessions = [
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=16,
            duration_min=90,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=16.5,
            duration_min=92,
        ),
    ]

    result = GoalProgressEngine().analyze_long_run_durability(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.trend is not None
    assert 0 < result.trend < 0.10


def test_long_run_durability_is_declining_when_recent_long_run_is_shorter():
    previous_sessions = [
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=18,
            duration_min=100,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=15,
            duration_min=85,
        ),
    ]

    result = GoalProgressEngine().analyze_long_run_durability(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "declining"
    assert result.trend is not None
    assert result.trend < -0.10


def test_long_run_durability_has_insufficient_evidence_without_previous_long_run():
    recent_sessions = [
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=17,
            duration_min=95,
        ),
    ]

    result = GoalProgressEngine().analyze_long_run_durability(
        recent_sessions=recent_sessions,
        previous_sessions=[],
    )

    assert result.area == "long_run_durability"
    assert result.status == "insufficient_evidence"
    assert result.trend is None
    assert result.confidence == 0.3
    assert result.evidence

def test_threshold_development_is_improving_when_recent_threshold_volume_is_higher():
    previous_sessions = [
        make_session(
            session_id="previous-threshold",
            start_time=datetime(
                2026,
                7,
                3,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=10,
            duration_min=55,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-threshold-1",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=12,
            duration_min=65,
        ),
        make_session(
            session_id="recent-threshold-2",
            start_time=datetime(
                2026,
                8,
                5,
                17,
                0,
            ),
            workout_type="tempo_run",
            distance_km=8,
            duration_min=42,
        ),
    ]

    result = GoalProgressEngine().analyze_threshold_development(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.area == "threshold_development"
    assert result.status == "improving"
    assert result.trend is not None
    assert result.trend > 0
    assert result.confidence > 0
    assert result.evidence

def test_threshold_development_is_stable_when_duration_is_similar():
    previous_sessions = [
        make_session(
            session_id="previous-threshold",
            start_time=datetime(
                2026,
                7,
                3,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=10,
            duration_min=60,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-threshold",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="tempo_run",
            distance_km=10,
            duration_min=64,
        ),
    ]

    result = GoalProgressEngine().analyze_threshold_development(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.trend is not None
    assert 0 < result.trend < 0.10


def test_threshold_development_is_declining_when_recent_duration_is_lower():
    previous_sessions = [
        make_session(
            session_id="previous-threshold",
            start_time=datetime(
                2026,
                7,
                3,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=12,
            duration_min=70,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-threshold",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="tempo_run",
            distance_km=9,
            duration_min=55,
        ),
    ]

    result = GoalProgressEngine().analyze_threshold_development(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "declining"
    assert result.trend is not None
    assert result.trend < -0.10


def test_threshold_development_has_insufficient_evidence_without_previous_threshold():
    recent_sessions = [
        make_session(
            session_id="recent-threshold",
            start_time=datetime(
                2026,
                7,
                31,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=12,
            duration_min=65,
        ),
    ]

    result = GoalProgressEngine().analyze_threshold_development(
        recent_sessions=recent_sessions,
        previous_sessions=[],
    )

    assert result.area == "threshold_development"
    assert result.status == "insufficient_evidence"
    assert result.trend is None
    assert result.confidence == 0.3
    assert result.evidence

def test_high_aerobic_development_is_improving_when_recent_volume_is_higher():
    previous_sessions = [
        make_session(
            session_id="previous-vo2",
            start_time=datetime(
                2026,
                7,
                2,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=8,
            duration_min=45,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-vo2-1",
            start_time=datetime(
                2026,
                7,
                30,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=9,
            duration_min=50,
        ),
        make_session(
            session_id="recent-intervals",
            start_time=datetime(
                2026,
                8,
                4,
                17,
                0,
            ),
            workout_type="intervals",
            distance_km=8,
            duration_min=45,
        ),
    ]

    result = GoalProgressEngine().analyze_high_aerobic_development(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.area == "high_aerobic_development"
    assert result.status == "improving"
    assert result.trend is not None
    assert result.trend > 0
    assert result.confidence > 0
    assert result.evidence

def test_high_aerobic_development_is_stable_when_duration_is_similar():
    previous_sessions = [
        make_session(
            session_id="previous-vo2",
            start_time=datetime(
                2026,
                7,
                2,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=8,
            duration_min=50,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-intervals",
            start_time=datetime(
                2026,
                7,
                30,
                17,
                0,
            ),
            workout_type="intervals",
            distance_km=8,
            duration_min=53,
        ),
    ]

    result = GoalProgressEngine().analyze_high_aerobic_development(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.trend is not None
    assert 0 < result.trend < 0.10


def test_high_aerobic_development_is_declining_when_recent_duration_is_lower():
    previous_sessions = [
        make_session(
            session_id="previous-vo2",
            start_time=datetime(
                2026,
                7,
                2,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=9,
            duration_min=60,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-intervals",
            start_time=datetime(
                2026,
                7,
                30,
                17,
                0,
            ),
            workout_type="intervals",
            distance_km=7,
            duration_min=45,
        ),
    ]

    result = GoalProgressEngine().analyze_high_aerobic_development(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "declining"
    assert result.trend is not None
    assert result.trend < -0.10


def test_high_aerobic_development_has_insufficient_evidence_without_previous_high_aerobic():
    recent_sessions = [
        make_session(
            session_id="recent-vo2",
            start_time=datetime(
                2026,
                7,
                30,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=9,
            duration_min=50,
        ),
    ]

    result = GoalProgressEngine().analyze_high_aerobic_development(
        recent_sessions=recent_sessions,
        previous_sessions=[],
    )

    assert result.area == "high_aerobic_development"
    assert result.status == "insufficient_evidence"
    assert result.trend is None
    assert result.confidence == 0.3
    assert result.evidence

def test_race_performance_is_improving_when_recent_race_pace_is_faster():
    previous_sessions = [
        make_session(
            session_id="previous-race",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=40,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-race",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=39,
        ),
    ]

    result = GoalProgressEngine().analyze_race_performance(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.area == "race_performance"
    assert result.status == "improving"
    assert result.trend is not None
    assert result.trend > 0
    assert result.confidence > 0
    assert result.evidence

def test_race_performance_is_stable_when_recent_race_pace_is_similar():
    previous_sessions = [
        make_session(
            session_id="previous-race",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=40.0,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-race",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=39.8,
        ),
    ]

    result = GoalProgressEngine().analyze_race_performance(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.trend is not None
    assert 0 < result.trend < 0.01


def test_race_performance_is_declining_when_recent_race_pace_is_slower():
    previous_sessions = [
        make_session(
            session_id="previous-race",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=39,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-race",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=40,
        ),
    ]

    result = GoalProgressEngine().analyze_race_performance(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "declining"
    assert result.trend is not None
    assert result.trend < -0.01


def test_race_performance_has_insufficient_evidence_for_different_distances():
    previous_sessions = [
        make_session(
            session_id="previous-5k",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="race",
            distance_km=5,
            duration_min=18.5,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-10k",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="race",
            distance_km=10,
            duration_min=39,
        ),
    ]

    result = GoalProgressEngine().analyze_race_performance(
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.area == "race_performance"
    assert result.status == "insufficient_evidence"
    assert result.trend is None
    assert result.confidence == 0.3
    assert result.evidence

def test_goal_progress_is_progressing_when_majority_of_capabilities_improve():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    previous_sessions = [
        make_session(
            session_id="previous-easy",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=40,
            duration_min=220,
        ),
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=15,
            duration_min=85,
        ),
        make_session(
            session_id="previous-threshold",
            start_time=datetime(
                2026,
                7,
                8,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=10,
            duration_min=55,
        ),
        make_session(
            session_id="previous-vo2",
            start_time=datetime(
                2026,
                7,
                12,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=8,
            duration_min=45,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-easy",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=50,
            duration_min=275,
        ),
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=18,
            duration_min=100,
        ),
        make_session(
            session_id="recent-threshold",
            start_time=datetime(
                2026,
                8,
                5,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=12,
            duration_min=65,
        ),
        make_session(
            session_id="recent-vo2",
            start_time=datetime(
                2026,
                8,
                9,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=9,
            duration_min=50,
        ),
    ]

    result = GoalProgressEngine().analyze(
        goal=goal,
        target_date=date(
            2026,
            8,
            10,
        ),
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "progressing"
    assert result.fitness_trend == "improving"
    assert result.confidence > 0
    assert len(result.capabilities) == 5
    assert result.primary_limiter is None
    assert result.secondary_limiter is None
    assert result.evidence

def test_goal_progress_is_stable_when_available_capabilities_are_stable():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    previous_sessions = [
        make_session(
            session_id="previous-easy",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=40,
            duration_min=220,
        ),
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=16,
            duration_min=90,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-easy",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=41,
            duration_min=225,
        ),
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=16.5,
            duration_min=92,
        ),
    ]

    result = GoalProgressEngine().analyze(
        goal=goal,
        target_date=date(
            2026,
            8,
            10,
        ),
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.fitness_trend == "stable"


def test_goal_progress_remains_stable_when_majority_of_training_exposure_signals_decline_without_performance_evidence():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    previous_sessions = [
        make_session(
            session_id="previous-easy",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=60,
            duration_min=330,
        ),
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=18,
            duration_min=100,
        ),
        make_session(
            session_id="previous-threshold",
            start_time=datetime(
                2026,
                7,
                8,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=12,
            duration_min=70,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-easy",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=40,
            duration_min=220,
        ),
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=15,
            duration_min=85,
        ),
        make_session(
            session_id="recent-threshold",
            start_time=datetime(
                2026,
                8,
                5,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=9,
            duration_min=50,
        ),
    ]

    result = GoalProgressEngine().analyze(
        goal=goal,
        target_date=date(
            2026,
            8,
            10,
        ),
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status == "stable"
    assert result.fitness_trend == "stable"


def test_goal_progress_has_insufficient_evidence_without_training_history():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    result = GoalProgressEngine().analyze(
        goal=goal,
        target_date=date(
            2026,
            8,
            10,
        ),
        recent_sessions=[],
        previous_sessions=[],
    )

    assert result.status == "insufficient_evidence"
    assert (
        result.fitness_trend
        == "insufficient_evidence"
    )
    assert result.confidence >= 0
    assert len(result.capabilities) == 5

def test_goal_progress_does_not_call_reduced_training_exposure_regression_without_performance_evidence():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    previous_sessions = [
        make_session(
            session_id="previous-easy",
            start_time=datetime(
                2026,
                7,
                1,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=60,
            duration_min=330,
        ),
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=20,
            duration_min=110,
        ),
        make_session(
            session_id="previous-vo2",
            start_time=datetime(
                2026,
                7,
                10,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=10,
            duration_min=70,
        ),
        make_session(
            session_id="previous-threshold",
            start_time=datetime(
                2026,
                7,
                12,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=10,
            duration_min=55,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-easy",
            start_time=datetime(
                2026,
                7,
                29,
                17,
                0,
            ),
            workout_type="easy_run",
            distance_km=48,
            duration_min=265,
        ),
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=18,
            duration_min=100,
        ),
        make_session(
            session_id="recent-vo2",
            start_time=datetime(
                2026,
                8,
                5,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=9,
            duration_min=55,
        ),
        make_session(
            session_id="recent-threshold",
            start_time=datetime(
                2026,
                8,
                8,
                17,
                0,
            ),
            workout_type="threshold",
            distance_km=12,
            duration_min=70,
        ),
    ]

    result = GoalProgressEngine().analyze(
        goal=goal,
        target_date=date(
            2026,
            8,
            10,
        ),
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.status != "regressing"

def test_goal_progress_does_not_treat_reduced_training_exposure_as_confirmed_limiter():
    goal = Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            10,
            1,
        ),
        priority="A",
    )

    previous_sessions = [
        make_session(
            session_id="previous-long",
            start_time=datetime(
                2026,
                7,
                5,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=20,
            duration_min=110,
        ),
        make_session(
            session_id="previous-vo2",
            start_time=datetime(
                2026,
                7,
                10,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=12,
            duration_min=80,
        ),
    ]

    recent_sessions = [
        make_session(
            session_id="recent-long",
            start_time=datetime(
                2026,
                8,
                2,
                9,
                0,
            ),
            workout_type="easy_run",
            distance_km=18,
            duration_min=100,
        ),
        make_session(
            session_id="recent-vo2",
            start_time=datetime(
                2026,
                8,
                5,
                17,
                0,
            ),
            workout_type="vo2max",
            distance_km=10,
            duration_min=60,
        ),
    ]

    result = GoalProgressEngine().analyze(
        goal=goal,
        target_date=date(
            2026,
            8,
            10,
        ),
        recent_sessions=recent_sessions,
        previous_sessions=previous_sessions,
    )

    assert result.primary_limiter is None
    assert result.secondary_limiter is None