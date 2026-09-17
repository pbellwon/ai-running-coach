from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    sessionmaker,
)

from app.db.database import Base
from app.db.models import AIExplanationDB
from app.services.ai_explanation_cache_service import (
    AIExplanationCacheService,
)


def make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
    )

    Base.metadata.create_all(
        bind=engine
    )

    return sessionmaker(
        bind=engine
    )


def test_build_context_hash_is_stable():
    service = AIExplanationCacheService(
        session_factory=(
            make_session_factory()
        )
    )

    first = service.build_context_hash(
        {
            "decision":
                "do_as_planned",
            "confidence":
                0.9,
            "context": {
                "b": 2,
                "a": 1,
            },
        }
    )

    second = service.build_context_hash(
        {
            "context": {
                "a": 1,
                "b": 2,
            },
            "confidence":
                0.9,
            "decision":
                "do_as_planned",
        }
    )

    assert first == second


def test_build_context_hash_changes_when_context_changes():
    service = AIExplanationCacheService(
        session_factory=(
            make_session_factory()
        )
    )

    first = service.build_context_hash(
        {
            "decision":
                "do_as_planned",
            "confidence":
                0.9,
        }
    )

    second = service.build_context_hash(
        {
            "decision":
                "do_as_planned",
            "confidence":
                0.8,
        }
    )

    assert first != second


def test_save_and_get_cached_explanation():
    session_factory = (
        make_session_factory()
    )

    service = AIExplanationCacheService(
        session_factory=(
            session_factory
        )
    )

    context_hash = (
        service.build_context_hash(
            {
                "status":
                    "completed",
                "distance_km":
                    17.05,
            }
        )
    )

    saved = service.save(
        explanation_type="today",
        target_date="2026-09-13",
        context_hash=(
            context_hash
        ),
        model="test-model",
        explanation_text=(
            "Workout completed."
        ),
    )

    assert isinstance(
        saved,
        AIExplanationDB,
    )

    cached = service.get(
        context_hash
    )

    assert cached is not None

    assert (
        cached.explanation_type
        == "today"
    )

    assert (
        cached.target_date
        == datetime(
            2026,
            9,
            13,
        )
    )

    assert (
        cached.model
        == "test-model"
    )

    assert (
        cached.explanation_text
        == "Workout completed."
    )


def test_save_updates_existing_hash():
    session_factory = (
        make_session_factory()
    )

    service = AIExplanationCacheService(
        session_factory=(
            session_factory
        )
    )

    context_hash = (
        service.build_context_hash(
            {
                "status":
                    "ready"
            }
        )
    )

    first = service.save(
        explanation_type="today",
        target_date="2026-09-13",
        context_hash=(
            context_hash
        ),
        model="model-a",
        explanation_text="First",
    )

    second = service.save(
        explanation_type="today",
        target_date="2026-09-13",
        context_hash=(
            context_hash
        ),
        model="model-b",
        explanation_text="Second",
    )

    assert first.id == second.id

    cached = service.get(
        context_hash
    )

    assert cached is not None

    assert (
        cached.model
        == "model-b"
    )

    assert (
        cached.explanation_text
        == "Second"
    )