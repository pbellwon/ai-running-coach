from dataclasses import dataclass
from datetime import (
    date,
    datetime,
)

from app.models.coach_context import (
    CoachContext,
)
from app.models.goal import Goal
from app.services.coach_context_service import (
    CoachContextService,
)


@dataclass
class FakeToday:
    target_date: str
    status: str
    planned_workout: dict
    recovery: dict


@dataclass
class FakeGoalProgress:
    status: str
    confidence: float
    target_date: date


@dataclass
class FakeMemory:
    id: int
    category: str
    memory_text: str
    source: str
    confidence: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FakeTodayService:
    def __init__(self):
        self.received_target_date = None

    def build(
        self,
        target_date,
    ):
        self.received_target_date = (
            target_date
        )

        return FakeToday(
            target_date=target_date,
            status="ready",
            planned_workout={
                "title": "Threshold",
                "workout_type": (
                    "threshold"
                ),
            },
            recovery={
                "overall_status":
                    "good",
            },
        )


class FakeGoalProgressService:
    def __init__(self):
        self.received_goal = None
        self.received_target_date = None

    def build(
        self,
        goal,
        target_date,
    ):
        self.received_goal = goal
        self.received_target_date = (
            target_date
        )

        return FakeGoalProgress(
            status="stable",
            confidence=0.72,
            target_date=target_date,
        )


class FakeAthleteMemoryService:
    def list_active(
        self,
    ):
        timestamp = datetime(
            2026,
            9,
            13,
            12,
            0,
        )

        return [
            FakeMemory(
                id=1,
                category="environment",
                memory_text=(
                    "Gorzej znoszę "
                    "treningi i zawody "
                    "w upale."
                ),
                source="athlete",
                confidence=1.0,
                is_active=True,
                created_at=timestamp,
                updated_at=timestamp,
            )
        ]


class FakeCurrentGoalService:
    def __init__(
        self,
        goal,
    ):
        self.goal = goal
        self.call_count = 0

    def get(
        self,
    ):
        self.call_count += 1
        return self.goal


def make_goal():
    return Goal(
        goal_type="race_time",
        distance_km=10,
        target_time_sec=2310,
        target_date=date(
            2026,
            11,
            11,
        ),
        priority="A",
        notes=(
            "Target 38:30 for 10K."
        ),
    )


def make_service():
    goal = make_goal()

    today_service = (
        FakeTodayService()
    )

    progress_service = (
        FakeGoalProgressService()
    )

    memory_service = (
        FakeAthleteMemoryService()
    )

    current_goal_service = (
        FakeCurrentGoalService(
            goal
        )
    )

    service = CoachContextService(
        today_service=today_service,
        goal_progress_service=(
            progress_service
        ),
        athlete_memory_service=(
            memory_service
        ),
        current_goal_service=(
            current_goal_service
        ),
    )

    return (
        service,
        goal,
        today_service,
        progress_service,
        current_goal_service,
    )


def test_builds_structured_coach_context():
    (
        service,
        _,
        _,
        _,
        _,
    ) = make_service()

    result = service.build(
        target_date="2026-09-13",
    )

    assert isinstance(
        result,
        CoachContext,
    )

    assert (
        result.schema_version
        == "1.0"
    )

    assert (
        result.target_date
        == "2026-09-13"
    )

    assert (
        result.goal[
            "goal_type"
        ]
        == "race_time"
    )

    assert (
        result.goal[
            "distance_km"
        ]
        == 10
    )

    assert (
        result.goal[
            "target_time_sec"
        ]
        == 2310
    )

    assert (
        result.goal[
            "target_date"
        ]
        == "2026-11-11"
    )

    assert (
        result.today[
            "status"
        ]
        == "ready"
    )

    assert (
        result.today[
            "recovery"
        ][
            "overall_status"
        ]
        == "good"
    )

    assert (
        result.goal_progress[
            "status"
        ]
        == "stable"
    )

    assert (
        result.goal_progress[
            "confidence"
        ]
        == 0.72
    )

    assert (
        result.goal_progress[
            "target_date"
        ]
        == "2026-09-13"
    )

    assert (
        len(
            result.athlete_memory
        )
        == 1
    )

    assert (
        result.athlete_memory[
            0
        ][
            "category"
        ]
        == "environment"
    )


def test_loads_current_goal_and_passes_it_to_goal_progress():
    (
        service,
        goal,
        _,
        progress_service,
        current_goal_service,
    ) = make_service()

    service.build(
        target_date="2026-09-13",
    )

    assert (
        current_goal_service.call_count
        == 1
    )

    assert (
        progress_service
        .received_goal
        is goal
    )

    assert (
        progress_service
        .received_target_date
        == date(
            2026,
            9,
            13,
        )
    )


def test_passes_iso_date_to_today_service():
    (
        service,
        _,
        today_service,
        _,
        _,
    ) = make_service()

    service.build(
        target_date=date(
            2026,
            9,
            13,
        ),
    )

    assert (
        today_service
        .received_target_date
        == "2026-09-13"
    )


def test_accepts_datetime_target_date():
    (
        service,
        _,
        _,
        _,
        _,
    ) = make_service()

    result = service.build(
        target_date=datetime(
            2026,
            9,
            13,
            18,
            30,
        ),
    )

    assert (
        result.target_date
        == "2026-09-13"
    )


def test_rejects_invalid_date_string():
    (
        service,
        _,
        _,
        _,
        _,
    ) = make_service()

    try:
        service.build(
            target_date="13-09-2026",
        )

    except ValueError as exc:
        assert (
            str(exc)
            == (
                "Date must use "
                "YYYY-MM-DD format."
            )
        )

    else:
        raise AssertionError(
            "Expected ValueError."
        )