from datetime import datetime

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.models.athlete_memory import AthleteMemory
from app.models.workout_feedback import WorkoutFeedback


client = TestClient(app)


class FakeWorkoutFeedbackService:
    stored = None

    def upsert(
        self,
        session_id,
        perceived_effort,
        execution_feeling,
        comment,
    ):
        now = datetime(
            2026,
            9,
            6,
            18,
            0,
        )

        result = WorkoutFeedback(
            session_id=session_id,
            perceived_effort=perceived_effort,
            execution_feeling=execution_feeling,
            comment=comment,
            created_at=now,
            updated_at=now,
        )

        FakeWorkoutFeedbackService.stored = result

        return result

    def get(
        self,
        session_id,
    ):
        stored = FakeWorkoutFeedbackService.stored

        if (
            stored is not None
            and stored.session_id == session_id
        ):
            return stored

        return None


class FakeAthleteMemoryService:
    items = []

    def create(
        self,
        category,
        memory_text,
        source,
        confidence,
    ):
        now = datetime(
            2026,
            9,
            6,
            18,
            0,
        )

        item = AthleteMemory(
            id=len(
                FakeAthleteMemoryService.items
            ) + 1,
            category=category,
            memory_text=memory_text,
            source=source,
            confidence=confidence,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        FakeAthleteMemoryService.items.append(
            item
        )

        return item

    def list_active(self):
        return [
            item
            for item in FakeAthleteMemoryService.items
            if item.is_active
        ]

    def update(
        self,
        memory_id,
        category,
        memory_text,
        source,
        confidence,
    ):
        for item in FakeAthleteMemoryService.items:
            if item.id != memory_id:
                continue

            item.category = category
            item.memory_text = memory_text
            item.source = source
            item.confidence = confidence

            return item

        return None

    def deactivate(
        self,
        memory_id,
    ):
        for item in FakeAthleteMemoryService.items:
            if item.id != memory_id:
                continue

            item.is_active = False

            return item

        return None


def setup_function():
    FakeWorkoutFeedbackService.stored = None
    FakeAthleteMemoryService.items = []


def test_workout_feedback_round_trip(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "WorkoutFeedbackService",
        FakeWorkoutFeedbackService,
    )

    response = client.post(
        "/feedback/workout",
        json={
            "session_id": "session:test.fit",
            "perceived_effort": 7,
            "execution_feeling": "on_target",
            "comment": "Controlled.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["session_id"]
        == "session:test.fit"
    )
    assert data["perceived_effort"] == 7
    assert (
        data["execution_feeling"]
        == "on_target"
    )

    response = client.get(
        "/feedback/workout/session:test.fit"
    )

    assert response.status_code == 200
    assert (
        response.json()["comment"]
        == "Controlled."
    )


def test_workout_feedback_rejects_invalid_feeling(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "WorkoutFeedbackService",
        FakeWorkoutFeedbackService,
    )

    response = client.post(
        "/feedback/workout",
        json={
            "session_id": "session:test.fit",
            "perceived_effort": 7,
            "execution_feeling": "terrible",
        },
    )

    assert response.status_code == 400


def test_workout_feedback_returns_404_when_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "WorkoutFeedbackService",
        FakeWorkoutFeedbackService,
    )

    response = client.get(
        "/feedback/workout/missing"
    )

    assert response.status_code == 404


def test_legacy_memory_reads_require_access_and_writes_use_confirmation(monkeypatch):
    monkeypatch.setenv('COACH_CHAT_ACCESS_CODE', 'test-memory-owner-code')
    monkeypatch.setattr(main_module, 'AthleteMemoryService', FakeAthleteMemoryService)
    assert client.get('/memory').status_code == 401
    headers = {'Authorization': 'Bearer test-memory-owner-code'}
    assert client.get('/memory', headers=headers).status_code == 200
    for method, path in [('POST','/memory'),('PATCH','/memory/1'),('POST','/memory/1/deactivate')]:
        assert client.request(method, path, headers=headers, json={}).status_code == 410
