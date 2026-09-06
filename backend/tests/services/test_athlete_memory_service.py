from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.services.athlete_memory_service import (
    AthleteMemoryService,
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


def test_athlete_memory_service_creates_memory():
    session_factory = build_session_factory()

    service = AthleteMemoryService(
        session_factory=session_factory,
    )

    result = service.create(
        category="training_preference",
        memory_text=(
            "Prefers quality sessions on Tuesdays."
        ),
        source="athlete",
        confidence=1.0,
    )

    assert result.id is not None
    assert (
        result.category
        == "training_preference"
    )
    assert (
        result.memory_text
        == "Prefers quality sessions on Tuesdays."
    )
    assert result.source == "athlete"
    assert result.confidence == 1.0
    assert result.is_active is True
    assert result.created_at is not None
    assert result.updated_at is not None


def test_athlete_memory_service_lists_active_memories():
    session_factory = build_session_factory()

    service = AthleteMemoryService(
        session_factory=session_factory,
    )

    first = service.create(
        category="environment",
        memory_text="Performs poorly in heat.",
        source="athlete",
        confidence=1.0,
    )

    second = service.create(
        category="training_response",
        memory_text=(
            "Heavy strength work affects next-day running."
        ),
        source="athlete",
        confidence=0.9,
    )

    service.deactivate(
        memory_id=first.id,
    )

    result = service.list_active()

    assert len(result) == 1
    assert result[0].id == second.id


def test_athlete_memory_service_updates_memory():
    session_factory = build_session_factory()

    service = AthleteMemoryService(
        session_factory=session_factory,
    )

    created = service.create(
        category="preference",
        memory_text="Prefers morning runs.",
        source="athlete",
        confidence=0.8,
    )

    updated = service.update(
        memory_id=created.id,
        category="preference",
        memory_text="Prefers evening runs.",
        source="athlete",
        confidence=1.0,
    )

    assert updated is not None
    assert updated.id == created.id
    assert (
        updated.memory_text
        == "Prefers evening runs."
    )
    assert updated.confidence == 1.0
    assert updated.created_at == created.created_at
    assert (
        updated.updated_at
        >= created.updated_at
    )


def test_athlete_memory_service_returns_none_for_unknown_memory():
    session_factory = build_session_factory()

    service = AthleteMemoryService(
        session_factory=session_factory,
    )

    result = service.update(
        memory_id=999,
        category="preference",
        memory_text="Unknown.",
        source="athlete",
        confidence=1.0,
    )

    assert result is None


def test_athlete_memory_service_deactivates_memory():
    session_factory = build_session_factory()

    service = AthleteMemoryService(
        session_factory=session_factory,
    )

    created = service.create(
        category="environment",
        memory_text="Dislikes heat.",
        source="athlete",
        confidence=1.0,
    )

    result = service.deactivate(
        memory_id=created.id,
    )

    assert result is not None
    assert result.is_active is False