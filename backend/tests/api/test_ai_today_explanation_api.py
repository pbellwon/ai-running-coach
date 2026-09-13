from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class FakeAITodayExplanationService:
    def build(
        self,
        target_date: str,
    ) -> str:
        return (
            "Dzisiejsze zalecenie wynika z dobrego "
            "statusu regeneracji i braku sygnałów zmęczenia."
        )


def test_ai_today_explanation_endpoint(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(
        main,
        "AITodayExplanationService",
        FakeAITodayExplanationService,
    )

    response = client.get(
        "/explain/today/ai",
        params={
            "target_date":
                "2026-09-13",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["target_date"]
        == "2026-09-13"
    )

    assert (
        data["explanation"]
        == (
            "Dzisiejsze zalecenie wynika z dobrego "
            "statusu regeneracji i braku sygnałów zmęczenia."
        )
    )


class FailingAITodayExplanationService:
    def build(
        self,
        target_date: str,
    ) -> str:
        raise RuntimeError(
            "LLM unavailable"
        )


def test_ai_today_explanation_endpoint_handles_llm_error(
    monkeypatch,
):
    from app import main

    monkeypatch.setattr(
        main,
        "AITodayExplanationService",
        FailingAITodayExplanationService,
    )

    response = client.get(
        "/explain/today/ai",
        params={
            "target_date":
                "2026-09-13",
        },
    )

    assert response.status_code == 502

    assert (
        response.json()["detail"]
        == (
            "AI explanation is currently unavailable."
        )
    )