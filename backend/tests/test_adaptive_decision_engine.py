
from datetime import date

from app.engine.adaptive_decision_engine import AdaptiveDecisionEngine
from app.models.adaptive_feedback import AdaptiveFeedback
from app.models.planned_workout import PlannedWorkout


def make_workout() -> PlannedWorkout:
    return PlannedWorkout(
        planned_date=date(2026, 9, 23),
        title="Easy run",
        description="Easy aerobic run",
        workout_type="easy",
        intent=None,
        planned_distance_km=10.0,
        planned_duration_min=55,
        structure=[],
        priority="normal",
    )


def make_assessment(
    decision: str = "continue_plan",
    confidence: float = 0.9,
) -> AdaptiveFeedback:
    return AdaptiveFeedback(
        decision=decision,
        risk_level="low",
        reason="Previous workout assessment.",
        next_action="Review next workout.",
        confidence=confidence,
        warnings=[],
    )


def test_keep_plan_when_assessment_supports_continuation():
    proposal = AdaptiveDecisionEngine().generate(
        next_workout=make_workout(),
        execution_assessment=make_assessment(),
    )

    assert proposal.decision == "keep_plan"
    assert proposal.target_date == date(2026, 9, 23)
    assert proposal.proposed_distance_km == 10.0
    assert proposal.proposed_duration_min == 55
    assert proposal.requires_athlete_approval is True


def test_low_confidence_requires_manual_review():
    proposal = AdaptiveDecisionEngine().generate(
        next_workout=make_workout(),
        execution_assessment=make_assessment(confidence=0.4),
    )

    assert proposal.decision == "manual_review"


def test_adjust_next_workout_requires_additional_context():
    proposal = AdaptiveDecisionEngine().generate(
        next_workout=make_workout(),
        execution_assessment=make_assessment(
            decision="adjust_next_workout",
        ),
    )

    assert proposal.decision == "manual_review"
    assert proposal.proposed_distance_km == 10.0
    assert proposal.proposed_duration_min == 55

def make_recent_review(
    status: str,
    confidence: float = 0.9,
) -> dict:
    return {
        "date": "2026-09-21",
        "review": {
            "status": status,
            "confidence": confidence,
        },
    }


def test_repeated_difficulty_requires_manual_review():
    proposal = AdaptiveDecisionEngine().generate(
        next_workout=make_workout(),
        execution_assessment=make_assessment(),
        recent_reviews=[
            make_recent_review("too_hard"),
            make_recent_review("on_target"),
            make_recent_review("too_hard"),
        ],
    )

    assert proposal.decision == "manual_review"
    assert "Multiple recent sessions" in proposal.reason
    assert proposal.proposed_distance_km == 10.0


def test_single_difficult_session_does_not_trigger_review():
    proposal = AdaptiveDecisionEngine().generate(
        next_workout=make_workout(),
        execution_assessment=make_assessment(),
        recent_reviews=[
            make_recent_review("too_hard"),
            make_recent_review("on_target"),
            make_recent_review("on_target"),
        ],
    )

    assert proposal.decision == "keep_plan"


def test_low_confidence_difficulty_is_not_counted():
    proposal = AdaptiveDecisionEngine().generate(
        next_workout=make_workout(),
        execution_assessment=make_assessment(),
        recent_reviews=[
            make_recent_review("too_hard", confidence=0.4),
            make_recent_review("too_hard", confidence=0.9),
            make_recent_review("on_target"),
        ],
    )

    assert proposal.decision == "keep_plan"