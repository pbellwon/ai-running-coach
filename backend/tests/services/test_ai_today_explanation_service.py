import json

from app.models.today_explanation import (
    TodayExplanation,
)
from app.services.ai_today_explanation_service import (
    AITodayExplanationService,
)


class FakeExplanationService:
    def __init__(self):
        self.received_target_date = None

    def build(
        self,
        target_date,
    ):
        self.received_target_date = (
            target_date
        )

        return TodayExplanation(
            target_date="2026-09-13",
            status="ready",
            decision="do_as_planned",
            recommendation_type=(
                "as_planned"
            ),
            confidence=0.9,
            key_reasons=[
                (
                    "No strong recovery "
                    "or fatigue signal requires "
                    "a training change."
                )
            ],
            warnings=[],
            uncertainties=[],
            context={
                "goal": {
                    "distance_km": 10,
                    "target_time_sec": 2310,
                },
                "today": {
                    "planned_workout": {
                        "title": "Long",
                        "workout_type": (
                            "long_run"
                        ),
                        "planned_distance_km": (
                            17.0
                        ),
                    }
                },
            },
        )


class FakeLLMClient:
    def __init__(self):
        self.calls = []

    def generate(
        self,
        instructions,
        input_text,
    ):
        self.calls.append(
            {
                "instructions":
                    instructions,
                "input_text":
                    input_text,
            }
        )

        return (
            "Możesz wykonać "
            "dzisiejszy trening "
            "zgodnie z planem."
        )


def test_builds_ai_explanation_from_deterministic_context():
    explanation_service = (
        FakeExplanationService()
    )

    llm_client = (
        FakeLLMClient()
    )

    service = AITodayExplanationService(
        explanation_service=(
            explanation_service
        ),
        llm_client=llm_client,
    )

    result = service.build(
        target_date="2026-09-13",
    )

    assert (
        result
        == (
            "Możesz wykonać "
            "dzisiejszy trening "
            "zgodnie z planem."
        )
    )

    assert (
        explanation_service
        .received_target_date
        == "2026-09-13"
    )

    assert (
        len(
            llm_client.calls
        )
        == 1
    )

    call = llm_client.calls[0]

    assert (
        "Do not invent facts."
        in call["instructions"]
    )

    payload = json.loads(
        call["input_text"]
    )

    assert (
        payload["decision"]
        == "do_as_planned"
    )

    assert (
        payload["confidence"]
        == 0.9
    )

    assert (
        payload[
            "context"
        ][
            "goal"
        ][
            "target_time_sec"
        ]
        == 2310
    )