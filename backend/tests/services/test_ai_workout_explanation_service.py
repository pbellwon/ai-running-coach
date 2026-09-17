import json

from app.models.workout_explanation import (
    WorkoutExplanation,
)
from app.services.ai_workout_explanation_service import (
    AIWorkoutExplanationService,
)


SESSION_ID = (
    "session:intervals_icu:i186147008"
)


class FakeWorkoutExplanationService:
    def __init__(self):
        self.received_session_id = None
        self.received_target_date = None

    def build(
        self,
        session_id,
        target_date=None,
    ):
        self.received_session_id = (
            session_id
        )

        self.received_target_date = (
            target_date
        )

        return WorkoutExplanation(
            session_id=SESSION_ID,
            target_date="2026-09-13",
            status="on_target",
            confidence=0.9,
            planned_workout={
                "title": "Long",
                "workout_type": (
                    "long_run"
                ),
                "planned_distance_km": (
                    17.0
                ),
            },
            executed_workout={
                "workout_type": (
                    "easy_run"
                ),
                "distance_km": 17.05,
                "duration_min": 87.8,
            },
            athlete_feedback={
                "perceived_effort": 6.0,
                "execution_feeling": (
                    "on_target"
                ),
                "comment": (
                    "Spokojnie i pod kontrolą."
                ),
            },
            key_evidence=[
                (
                    "Workout intent matched "
                    "the planned session."
                ),
                (
                    "Executed distance was "
                    "within the target range."
                ),
            ],
            warnings=[],
            uncertainties=[],
            context={
                "review": {
                    "status": "on_target",
                }
            },
        )


class FakeLLMClient:
    def __init__(self):
        self.calls = []
        self.model = "test-model"

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
            "Trening został wykonany "
            "zgodnie z założeniami."
        )


class FakeCachedItem:
    def __init__(
        self,
        explanation_text,
    ):
        self.explanation_text = (
            explanation_text
        )


class FakeCacheService:
    def __init__(
        self,
        cached_text=None,
    ):
        self.cached_text = (
            cached_text
        )

        self.hash_payloads = []
        self.get_calls = []
        self.save_calls = []

    def build_context_hash(
        self,
        payload,
    ):
        self.hash_payloads.append(
            payload
        )

        return "workout-context-hash"

    def get(
        self,
        context_hash,
    ):
        self.get_calls.append(
            context_hash
        )

        if self.cached_text is None:
            return None

        return FakeCachedItem(
            self.cached_text
        )

    def save(
        self,
        **kwargs,
    ):
        self.save_calls.append(
            kwargs
        )


def test_builds_ai_workout_explanation_on_cache_miss():
    explanation_service = (
        FakeWorkoutExplanationService()
    )

    llm_client = (
        FakeLLMClient()
    )

    cache_service = (
        FakeCacheService()
    )

    service = AIWorkoutExplanationService(
        explanation_service=(
            explanation_service
        ),
        llm_client=llm_client,
        cache_service=(
            cache_service
        ),
    )

    result = service.build(
        session_id=SESSION_ID,
        target_date="2026-09-13",
    )

    assert (
        result
        == (
            "Trening został wykonany "
            "zgodnie z założeniami."
        )
    )

    assert (
        explanation_service
        .received_session_id
        == SESSION_ID
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
        payload["status"]
        == "on_target"
    )

    assert (
        payload[
            "planned_workout"
        ][
            "planned_distance_km"
        ]
        == 17.0
    )

    assert (
        payload[
            "executed_workout"
        ][
            "distance_km"
        ]
        == 17.05
    )

    assert (
        payload[
            "athlete_feedback"
        ][
            "perceived_effort"
        ]
        == 6.0
    )

    assert (
        len(
            cache_service.save_calls
        )
        == 1
    )

    save_call = (
        cache_service
        .save_calls[0]
    )

    assert (
        save_call[
            "explanation_type"
        ]
        == "workout"
    )

    assert (
        save_call[
            "target_date"
        ]
        == "2026-09-13"
    )

    assert (
        save_call[
            "context_hash"
        ]
        == "workout-context-hash"
    )

    assert (
        save_call[
            "model"
        ]
        == "test-model"
    )

    assert (
        save_call[
            "explanation_text"
        ]
        == result
    )


def test_returns_cached_workout_explanation_without_llm():
    llm_client = (
        FakeLLMClient()
    )

    cache_service = (
        FakeCacheService(
            cached_text=(
                "Cached workout explanation."
            )
        )
    )

    service = AIWorkoutExplanationService(
        explanation_service=(
            FakeWorkoutExplanationService()
        ),
        llm_client=llm_client,
        cache_service=(
            cache_service
        ),
    )

    result = service.build(
        session_id=SESSION_ID,
    )

    assert (
        result
        == "Cached workout explanation."
    )

    assert (
        len(
            llm_client.calls
        )
        == 0
    )

    assert (
        len(
            cache_service.save_calls
        )
        == 0
    )


def test_workout_context_hash_receives_complete_payload():
    cache_service = (
        FakeCacheService(
            cached_text="Cached."
        )
    )

    service = AIWorkoutExplanationService(
        explanation_service=(
            FakeWorkoutExplanationService()
        ),
        llm_client=(
            FakeLLMClient()
        ),
        cache_service=(
            cache_service
        ),
    )

    service.build(
        session_id=SESSION_ID,
    )

    assert (
        len(
            cache_service.hash_payloads
        )
        == 1
    )

    payload = (
        cache_service
        .hash_payloads[0]
    )

    assert (
        payload[
            "session_id"
        ]
        == SESSION_ID
    )

    assert (
        payload[
            "status"
        ]
        == "on_target"
    )

    assert (
        payload[
            "athlete_feedback"
        ][
            "execution_feeling"
        ]
        == "on_target"
    )