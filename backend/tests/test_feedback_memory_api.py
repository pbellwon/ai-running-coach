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


def test_athlete_memory_create_list_update_and_deactivate(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "AthleteMemoryService",
        FakeAthleteMemoryService,
    )

    response = client.post(
        "/memory",
        json={
            "category": "environment",
            "memory_text": (
                "Performs poorly in heat."
            ),
            "confidence": 1.0,
        },
    )

    assert response.status_code == 200

    memory_id = response.json()["id"]

    response = client.get(
        "/memory"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.patch(
        f"/memory/{memory_id}",
        json={
            "category": "environment",
            "memory_text": (
                "Heat strongly affects performance."
            ),
            "confidence": 0.9,
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["memory_text"]
        == "Heat strongly affects performance."
    )

    response = client.post(
        f"/memory/{memory_id}/deactivate"
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = client.get(
        "/memory"
    )

    assert response.status_code == 200
    assert response.json() == []