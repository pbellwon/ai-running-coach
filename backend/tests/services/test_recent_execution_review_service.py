from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import WorkoutDB
from app.models.executed_session import (
    ExecutedSession,
)
from app.models.workout_execution_review import (
    WorkoutExecutionReview,
)
from app.services.recent_execution_review_service import (
    RecentExecutionReviewService,
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


class FakePlanSource:
    def fetch_rows(self):
        return [
            {
                "date": "2026-09-10",
            },
            {
                "date": "2026-09-11",
            },
        ]


class FakePlanImporter:
    def import_rows(
        self,
        rows,
    ):
        return [
            SimpleNamespace(
                planned_date=datetime(
                    2026,
                    9,
                    10,
                ).date(),
                title="Threshold",
                description="Threshold session",
                workout_type="threshold",
                planned_distance_km=10.0,
                planned_duration_min=50.0,
                priority="key",
            ),
            SimpleNamespace(
                planned_date=datetime(
                    2026,
                    9,
                    11,
                ).date(),
                title="Easy Run",
                description="Easy 8 km",
                workout_type="easy_run",
                planned_distance_km=8.0,
                planned_duration_min=45.0,
                priority="normal",
            ),
        ]


class FakeFeedbackService:
    def get(
        self,
        session_id,
    ):
        return None


class FakeSessionBuilder:
    def build(
        self,
        workouts,
    ):
        return [
            self._make_session(
                workout
            )
            for workout in workouts
        ]

    def _make_session(
        self,
        workout,
    ):
        return ExecutedSession(
            session_id=(
                f"session:"
                f"{workout.source_file}"
            ),
            start_time=(
                workout.start_time
            ),
            end_time=(
                workout.start_time
            ),
            sport_family="running",
            workout_type=(
                workout.declared_workout_type
                or "easy_run"
            ),
            confidence=0.8,
            classification_method="test",
            components=[],
            total_distance_km=(
                workout.distance_km
            ),
            total_duration_min=(
                workout.duration_sec / 60
            ),
            warnings=[],
        )


class FakeReviewEngine:
    def review(
        self,
        session,
        planned_workout,
        feedback,
    ):
        status = (
            "on_target"
            if planned_workout is not None
            else "insufficient_evidence"
        )

        return WorkoutExecutionReview(
            session_id=session.session_id,
            planned_workout_type=(
                planned_workout.workout_type
                if planned_workout
                is not None
                else None
            ),
            executed_workout_type=(
                session.workout_type
            ),
            status=status,
            confidence=0.8,
            planned_distance_km=(
                planned_workout
                .planned_distance_km
                if planned_workout
                is not None
                else None
            ),
            executed_distance_km=(
                session.total_distance_km
            ),
            planned_duration_min=(
                planned_workout
                .planned_duration_min
                if planned_workout
                is not None
                else None
            ),
            executed_duration_min=(
                session.total_duration_min
            ),
            athlete_feedback=None,
            evidence=[],
            warnings=[],
        )


def add_workout(
    session_factory,
    source_file,
    start_time,
    distance_km,
    duration_min,
    workout_type,
):
    db = session_factory()

    try:
        db.add(
            WorkoutDB(
                source_file=source_file,
                start_time=start_time,
                sport="running",
                distance_km=distance_km,
                duration_sec=(
                    duration_min * 60
                ),
                declared_workout_type=(
                    workout_type
                ),
            )
        )

        db.commit()

    finally:
        db.close()


def build_service(
    session_factory,
):
    return RecentExecutionReviewService(
        session_factory=session_factory,
        plan_source=FakePlanSource(),
        plan_importer=FakePlanImporter(),
        session_builder=FakeSessionBuilder(),
        feedback_service=FakeFeedbackService(),
        review_engine=FakeReviewEngine(),
    )


def test_returns_three_most_recent_sessions():
    session_factory = (
        build_session_factory()
    )

    add_workout(
        session_factory=session_factory,
        source_file="first.fit",
        start_time=datetime(
            2026,
            8,
            1,
            17,
            0,
        ),
        distance_km=8.0,
        duration_min=45.0,
        workout_type="easy_run",
    )

    add_workout(
        session_factory=session_factory,
        source_file="second.fit",
        start_time=datetime(
            2026,
            8,
            10,
            17,
            0,
        ),
        distance_km=9.0,
        duration_min=48.0,
        workout_type="easy_run",
    )

    add_workout(
        session_factory=session_factory,
        source_file="third.fit",
        start_time=datetime(
            2026,
            8,
            30,
            17,
            0,
        ),
        distance_km=10.0,
        duration_min=50.0,
        workout_type="threshold",
    )

    add_workout(
        session_factory=session_factory,
        source_file="fourth.fit",
        start_time=datetime(
            2026,
            9,
            11,
            17,
            0,
        ),
        distance_km=8.0,
        duration_min=45.0,
        workout_type="easy_run",
    )

    service = build_service(
        session_factory
    )

    result = service.build(
        target_date="2026-09-12",
        limit=3,
    )

    assert len(result) == 3

    assert [
        item["session_id"]
        for item in result
    ] == [
        "session:fourth.fit",
        "session:third.fit",
        "session:second.fit",
    ]


def test_includes_plan_and_review():
    session_factory = (
        build_session_factory()
    )

    add_workout(
        session_factory=session_factory,
        source_file="threshold.fit",
        start_time=datetime(
            2026,
            9,
            10,
            17,
            0,
        ),
        distance_km=10.0,
        duration_min=50.0,
        workout_type="threshold",
    )

    service = build_service(
        session_factory
    )

    result = service.build(
        target_date="2026-09-10",
    )

    assert len(result) == 1

    item = result[0]

    assert (
        item["planned_workout"]["title"]
        == "Threshold"
    )

    assert (
        item["review"]["status"]
        == "on_target"
    )

    assert (
        item["review"]
        ["planned_workout_type"]
        == "threshold"
    )


def test_marks_session_without_plan_as_insufficient_evidence():
    session_factory = (
        build_session_factory()
    )

    add_workout(
        session_factory=session_factory,
        source_file="unplanned.fit",
        start_time=datetime(
            2026,
            9,
            9,
            17,
            0,
        ),
        distance_km=9.0,
        duration_min=50.0,
        workout_type="easy_run",
    )

    service = build_service(
        session_factory
    )

    result = service.build(
        target_date="2026-09-09",
    )

    assert len(result) == 1

    assert (
        result[0]["planned_workout"]
        is None
    )

    assert (
        result[0]["review"]["status"]
        == "insufficient_evidence"
    )


def test_returns_empty_list_when_no_sessions_exist():
    session_factory = (
        build_session_factory()
    )

    service = build_service(
        session_factory
    )

    result = service.build(
        target_date="2026-09-11",
    )

    assert result == []
