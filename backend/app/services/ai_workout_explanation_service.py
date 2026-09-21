from __future__ import annotations

import json

from app.ai.openai_client import (
    PaceMindOpenAIClient,
)
from app.services.ai_explanation_cache_service import (
    AIExplanationCacheService,
)
from app.services.workout_explanation_service import (
    WorkoutExplanationService,
)


class AIWorkoutExplanationService:
    EXPLANATION_TYPE = "workout"
    PROMPT_VERSION = "1.2"

    INSTRUCTIONS = """
You are PaceMind, an evidence-based endurance running coach.

Explain one completed workout using only the structured
PaceMind context provided to you.

Rules:
- Do not invent facts.
- Do not change the deterministic review status.
- Treat the planned workout type as the primary session intent.
- Treat the executed workout type as the execution profile,
  not necessarily as the name of the session.
- If the plan says long_run and execution says easy_run,
  describe it as a long run performed mostly at easy intensity.
- Explicitly mention meaningful execution-structure features,
  such as a fast finish, progression, intervals or strides,
  when they are present.
- Compare planned and executed distance or duration when useful.
- In execution_structure segments, duration_sec and duration_min
  represent elapsed time and may include stopped-clock periods.
- moving_time_sec and moving_duration_min represent moving time.
  Use moving time when describing running duration or pace.
- avg_pace_sec_per_km is calculated from moving time when
  complete moving-time data is available.
- If moving_time_sec or avg_pace_sec_per_km is null, do not
  infer moving time or running pace from elapsed duration.
- For recoveries between repetitions, count only segments
  named recovery. Do not count transition as another recovery.
- Distinguish warmup from cooldown. Do not combine their
  distances or durations and describe the total as warmup.
- Use athlete feedback when available.
- If athlete feedback confirms or explains a detected feature,
  connect the two explicitly.
- Mention relevant warnings or uncertainty.
- Do not prescribe future training unless the structured
  context explicitly contains such a recommendation.
- Be concise and concrete.
- Answer in Polish.
- Return plain text only.
- Do not use Markdown formatting.
""".strip()

    def __init__(
        self,
        explanation_service=None,
        llm_client=None,
        cache_service=None,
    ):
        self.explanation_service = (
            explanation_service
            if explanation_service is not None
            else WorkoutExplanationService()
        )

        self.llm_client = (
            llm_client
            if llm_client is not None
            else PaceMindOpenAIClient()
        )

        self.cache_service = (
            cache_service
            if cache_service is not None
            else AIExplanationCacheService()
        )

    def build(
        self,
        session_id: str,
        target_date=None,
    ) -> str:
        explanation = (
            self.explanation_service.build(
                session_id=session_id,
                target_date=target_date,
            )
        )

        payload = {
            "prompt_version": (
                self.PROMPT_VERSION
            ),
            "session_id": (
                explanation.session_id
            ),
            "target_date": (
                explanation.target_date
            ),
            "status": (
                explanation.status
            ),
            "confidence": (
                explanation.confidence
            ),
            "planned_workout": (
                explanation.planned_workout
            ),
            "executed_workout": (
                explanation.executed_workout
            ),
            "execution_structure": (
                explanation.execution_structure
            ),
            "athlete_feedback": (
                explanation.athlete_feedback
            ),
            "key_evidence": (
                explanation.key_evidence
            ),
            "warnings": (
                explanation.warnings
            ),
            "uncertainties": (
                explanation.uncertainties
            ),
            "context": (
                explanation.context
            ),
        }

        context_hash = (
            self.cache_service
            .build_context_hash(
                payload
            )
        )

        cached = (
            self.cache_service.get(
                context_hash
            )
        )

        if cached is not None:
            return (
                cached.explanation_text
            )

        input_text = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )

        explanation_text = (
            self.llm_client.generate(
                instructions=(
                    self.INSTRUCTIONS
                ),
                input_text=(
                    input_text
                ),
            )
        )

        self.cache_service.save(
            explanation_type=(
                self.EXPLANATION_TYPE
            ),
            target_date=(
                explanation.target_date
            ),
            context_hash=(
                context_hash
            ),
            model=(
                self.llm_client.model
            ),
            explanation_text=(
                explanation_text
            ),
        )

        return explanation_text