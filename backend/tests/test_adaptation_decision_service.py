from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.adaptation_decision_record import (
    AdaptationDecisionRecord,
)
from app.services.adaptation_decision_service import (
    AdaptationDecisionService,
)


def test_save_adaptation_decision():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(
        bind=engine
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    service = AdaptationDecisionService(
        session_factory=TestingSessionLocal
    )

    result = service.save(
        target_date="2026-10-13",
        original_workout_type="threshold",
        proposed_workout_type="easy_run",
        proposal_decision="replace_with_easy",
        athlete_response="accepted",
    )

    assert isinstance(
        result,
        AdaptationDecisionRecord,
    )

    assert result.target_date == "2026-10-13"
    assert result.original_workout_type == "threshold"
    assert result.proposed_workout_type == "easy_run"
    assert result.proposal_decision == "replace_with_easy"
    assert result.athlete_response == "accepted"
    assert result.created_at is not None