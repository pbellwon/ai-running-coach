from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import (
    LapDB,
    WorkoutDB,
)
from app.services.intervals_activity_sync_service import (
    IntervalsActivitySyncService,
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


class FakeClient:
    def get_activities(
        self,
        oldest,
        newest,
    ):
        return [
            {
                "id": "i123",
            }
        ]

    def get_activity_with_intervals(
        self,
        activity_id,
    ):
        assert activity_id == "i123"

        return {
            "icu_intervals": [
                {
                    "distance": 1000.0,
                    "elapsed_time": 330,
                    "average_heartrate": 138,
                    "max_heartrate": 145,
                },
                {
                    "distance": 1002.6,
                    "elapsed_time": 245,
                    "average_heartrate": 159,
                    "max_heartrate": 168,
                },
            ]
        }


class FakeActivityMapper:
    def map(
        self,
        activity,
    ):
        assert activity["id"] == "i123"

        return WorkoutDB(
            source_file="intervals_icu:i123",
            start_time=datetime(
                2026,
                9,
                13,
                9,
                0,
            ),
            sport="running",
            distance_km=2.0026,
            duration_sec=575.0,
            avg_hr=145.0,
            max_hr=168.0,
            avg_pace_sec_per_km=287.5,
            records_count=None,
            laps_count=2,
            activity_name="Test Run",
            description=None,
            external_type="Run",
            source_platform="intervals_icu",
            training_load=None,
            rpe=None,
            race=False,
            interval_summary=None,
            declared_workout_type="easy_run",
            declared_session_role=None,
        )


def build_service(
    session_factory,
):
    return IntervalsActivitySyncService(
        client=FakeClient(),
        mapper=FakeActivityMapper(),
        session_factory=session_factory,
    )


def test_sync_creates_workout_and_laps():
    session_factory = (
        build_session_factory()
    )

    service = build_service(
        session_factory
    )

    result = service.sync(
        oldest="2026-09-13",
        newest="2026-09-13",
    )

    assert result["fetched"] == 1
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["skipped"] == 0

    assert (
        result["laps_created"]
        == 2
    )

    assert (
        result["laps_replaced"]
        == 0
    )

    db = session_factory()

    try:
        workouts = (
            db.query(WorkoutDB)
            .all()
        )

        laps = (
            db.query(LapDB)
            .order_by(
                LapDB.lap_number
            )
            .all()
        )

        assert len(workouts) == 1
        assert len(laps) == 2

        assert (
            workouts[0].source_file
            == "intervals_icu:i123"
        )

        assert (
            laps[0].workout_file
            == "intervals_icu:i123"
        )

        assert (
            laps[0].lap_number
            == 1
        )

        assert (
            laps[1].lap_number
            == 2
        )

        assert (
            laps[1].elapsed_time_sec
            == 245.0
        )

    finally:
        db.close()


def test_second_sync_replaces_laps_without_duplicates():
    session_factory = (
        build_session_factory()
    )

    service = build_service(
        session_factory
    )

    first = service.sync(
        oldest="2026-09-13",
        newest="2026-09-13",
    )

    second = service.sync(
        oldest="2026-09-13",
        newest="2026-09-13",
    )

    assert (
        first["created"]
        == 1
    )

    assert (
        second["updated"]
        == 1
    )

    assert (
        second["laps_created"]
        == 2
    )

    assert (
        second["laps_replaced"]
        == 2
    )

    db = session_factory()

    try:
        assert (
            db.query(WorkoutDB)
            .count()
            == 1
        )

        assert (
            db.query(LapDB)
            .count()
            == 2
        )

    finally:
        db.close()


def test_laps_are_linked_by_workout_source_file():
    session_factory = (
        build_session_factory()
    )

    service = build_service(
        session_factory
    )

    service.sync(
        oldest="2026-09-13",
        newest="2026-09-13",
    )

    db = session_factory()

    try:
        workout = (
            db.query(WorkoutDB)
            .first()
        )

        laps = (
            db.query(LapDB)
            .filter(
                LapDB.workout_file
                == workout.source_file
            )
            .all()
        )

        assert len(laps) == 2

    finally:
        db.close()