from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.services.workout_feedback_service import (
    WorkoutFeedbackService,
)


def build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        bind=engine
    )

    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def test_workout_feedback_service_creates_feedback():
    session_factory = build_session_factory()

    service = WorkoutFeedbackService(
        session_factory=session_factory,
    )

    result = service.upsert(
        session_id="2026-09-01-session-1",
        perceived_effort=7.0,
        execution_feeling="on_target",
        comment="Controlled but demanding.",
    )

    assert (
        result.session_id
        == "2026-09-01-session-1"
    )
    assert result.perceived_effort == 7.0
    assert (
        result.execution_feeling
        == "on_target"
    )
    assert (
        result.comment
        == "Controlled but demanding."
    )
    assert result.created_at is not None
    assert result.updated_at is not None


def test_workout_feedback_service_updates_existing_feedback():
    session_factory = build_session_factory()

    service = WorkoutFeedbackService(
        session_factory=session_factory,
    )

    first = service.upsert(
        session_id="2026-09-01-session-1",
        perceived_effort=7.0,
        execution_feeling="on_target",
        comment="Initial feedback.",
    )

    updated = service.upsert(
        session_id="2026-09-01-session-1",
        perceived_effort=8.0,
        execution_feeling="too_hard",
        comment="Harder than expected.",
    )

    assert updated.session_id == first.session_id
    assert updated.perceived_effort == 8.0
    assert (
        updated.execution_feeling
        == "too_hard"
    )
    assert (
        updated.comment
        == "Harder than expected."
    )
    assert updated.created_at == first.created_at
    assert (
        updated.updated_at
        >= first.updated_at
    )


def test_workout_feedback_service_gets_feedback_by_session_id():
    session_factory = build_session_factory()

    service = WorkoutFeedbackService(
        session_factory=session_factory,
    )

    service.upsert(
        session_id="2026-09-01-session-1",
        perceived_effort=6.0,
        execution_feeling="on_target",
        comment=None,
    )

    result = service.get(
        session_id="2026-09-01-session-1",
    )

    assert result is not None
    assert (
        result.session_id
        == "2026-09-01-session-1"
    )
    assert result.perceived_effort == 6.0


def test_workout_feedback_service_returns_none_for_unknown_session():
    session_factory = build_session_factory()

    service = WorkoutFeedbackService(
        session_factory=session_factory,
    )

    result = service.get(
        session_id="missing-session",
    )

    assert result is None