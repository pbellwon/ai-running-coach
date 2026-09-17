from fastapi.testclient import TestClient

from app.main import app
from app.models.workout_explanation import (
    WorkoutExplanation,
)


client = TestClient(app)

SESSION_ID = (
    "session:intervals_icu:i186147008"
)


class FakeWorkoutExplanationService:
    def build(
        self,
        session_id,
        target_date=None,
    ):
        return WorkoutExplanation(
            session_id=session_id,
            target_date="2026-09-13",
            status="on_target",
            confidence=0.9,
            planned_workout={
                "title": "Long",
            },
            executed_workout={
                "distance_km": 17.05,
            },
            athlete_feedback={
                "perceived_effort": 6.0,
            },
            key_evidence=[
                "Distance matched."
            ],
            warnings=[],
            uncertainties=[],
            context={},
        )


class MissingWorkoutExplanationService:
    def build(
        self,
        session_id,
        target_date=None,
    ):
        raise LookupError(
            "Workout session was not found."
        )


class FakeAIWorkoutExplanationService:
    def build(
        self,
        session_id,
        target_date=None,
    ):
        return (
            "Trening został wykonany "
            "zgodnie z założeniami."
        )


class FailingAIWorkoutExplanationService:
    def build(
        self,
        session_id,
        target_date=None,
    ):
        raise RuntimeError(
            "LLM unavailable"
        )


def test_workout_explanation_endpoint(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(
        main,
        "WorkoutExplanationService",
        FakeWorkoutExplanationService,
    )

    response = client.get(
        f"/explain/workout/{SESSION_ID}",
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["session_id"]
        == SESSION_ID
    )

    assert (
        data["status"]
        == "on_target"
    )

    assert (
        data["confidence"]
        == 0.9
    )


def test_workout_explanation_returns_404(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(
        main,
        "WorkoutExplanationService",
        MissingWorkoutExplanationService,
    )

    response = client.get(
        f"/explain/workout/{SESSION_ID}",
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Workout session was not found."
    )


def test_ai_workout_explanation_endpoint(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(
        main,
        "AIWorkoutExplanationService",
        FakeAIWorkoutExplanationService,
    )

    response = client.get(
        f"/explain/workout/{SESSION_ID}/ai",
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["session_id"]
        == SESSION_ID
    )

    assert (
        data["explanation"]
        == (
            "Trening został wykonany "
            "zgodnie z założeniami."
        )
    )


def test_ai_workout_explanation_handles_llm_error(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(
        main,
        "AIWorkoutExplanationService",
        FailingAIWorkoutExplanationService,
    )

    response = client.get(
        f"/explain/workout/{SESSION_ID}/ai",
    )

    assert response.status_code == 502

    assert (
        response.json()["detail"]
        == (
            "AI workout explanation is currently unavailable."
        )
    )