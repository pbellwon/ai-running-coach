from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)


class FakeRecentExecutionReviewService:
    def build(
        self,
        target_date=None,
        limit=3,
    ):
        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        items = [
            {
                "session_id": "session:third.fit",
                "date": "2026-09-11",
                "start_time": "2026-09-11T17:00:00",
                "sport_family": "running",
                "workout_type": "easy_run",
                "distance_km": 8.0,
                "duration_min": 45.0,
                "activities_count": 1,
                "source_files": [
                    "third.fit",
                ],
                "planned_workout": {
                    "date": "2026-09-11",
                    "title": "Easy Run",
                    "workout_type": "easy_run",
                    "planned_distance_km": 8.0,
                    "planned_duration_min": 45.0,
                    "priority": "normal",
                },
                "review": {
                    "status": "on_target",
                    "confidence": 0.85,
                    "planned_workout_type": "easy_run",
                    "executed_workout_type": "easy_run",
                    "planned_distance_km": 8.0,
                    "executed_distance_km": 8.0,
                    "planned_duration_min": 45.0,
                    "executed_duration_min": 45.0,
                    "athlete_feedback": None,
                    "evidence": [
                        "Executed workout intent matched the plan.",
                    ],
                    "warnings": [],
                },
            },
            {
                "session_id": "session:second.fit",
                "date": "2026-09-10",
                "start_time": "2026-09-10T17:00:00",
                "sport_family": "running",
                "workout_type": "threshold",
                "distance_km": 10.0,
                "duration_min": 50.0,
                "activities_count": 1,
                "source_files": [
                    "second.fit",
                ],
                "planned_workout": {
                    "date": "2026-09-10",
                    "title": "Threshold",
                    "workout_type": "threshold",
                    "planned_distance_km": 10.0,
                    "planned_duration_min": 50.0,
                    "priority": "key",
                },
                "review": {
                    "status": "on_target",
                    "confidence": 0.9,
                    "planned_workout_type": "threshold",
                    "executed_workout_type": "threshold",
                    "planned_distance_km": 10.0,
                    "executed_distance_km": 10.0,
                    "planned_duration_min": 50.0,
                    "executed_duration_min": 50.0,
                    "athlete_feedback": None,
                    "evidence": [
                        "Executed workout intent matched the plan.",
                    ],
                    "warnings": [],
                },
            },
        ]

        return items[:limit]


def test_recent_workout_reviews_returns_items(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "RecentExecutionReviewService",
        FakeRecentExecutionReviewService,
    )

    response = client.get(
        "/workouts/recent-reviews",
        params={
            "target_date": "2026-09-11",
            "limit": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 2
    assert len(data["items"]) == 2

    assert (
        data["items"][0]["session_id"]
        == "session:third.fit"
    )

    assert (
        data["items"][0]["review"]["status"]
        == "on_target"
    )


def test_recent_workout_reviews_rejects_invalid_limit(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "RecentExecutionReviewService",
        FakeRecentExecutionReviewService,
    )

    response = client.get(
        "/workouts/recent-reviews",
        params={
            "limit": 0,
        },
    )

    assert response.status_code == 400

    assert (
        response.json()["detail"]
        == "limit must be greater than zero."
    )