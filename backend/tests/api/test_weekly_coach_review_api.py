from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_default_and_explicit_monday(monkeypatch):
    calls = []

    class Service:
        def build(self, week_start):
            calls.append(week_start)
            return {"status": "ready", "coach": {"headline": "Weekly review"}}

    monkeypatch.setattr(main, "WeeklyCoachReviewService", Service)
    assert client.get("/review/week").status_code == 200
    response = client.get("/review/week?week_start=2025-06-02")
    assert response.status_code == 200
    assert response.json()["coach"]["headline"] == "Weekly review"
    assert calls == [None, date(2025, 6, 2)]


def test_bad_week_inputs_never_call_integrations(monkeypatch):
    def unexpected():
        raise AssertionError("Integrations should not be called")

    monkeypatch.setattr(main, "WeeklyCoachReviewService", unexpected)
    assert client.get("/review/week?week_start=not-a-date").status_code == 422
    assert client.get("/review/week?week_start=2025-06-03").status_code == 400
    future = date.today() - timedelta(days=date.today().weekday()) + timedelta(days=7)
    assert client.get(f"/review/week?week_start={future}").status_code == 400


def test_integration_failure_does_not_leak_details(monkeypatch):
    class BrokenService:
        def build(self, week_start):
            raise RuntimeError("private service account details")

    monkeypatch.setattr(main, "WeeklyCoachReviewService", BrokenService)
    response = client.get("/review/week")
    assert response.status_code == 502
    assert "private" not in response.text
    assert "try again" in response.json()["detail"]
